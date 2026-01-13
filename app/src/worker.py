import time
import logging
import cv2
import mss
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from typing import Dict, Any, Tuple, Optional

# 모듈 임포트
from src.load_image import load_templates
from src.load_build import BuildLoader
from src.load_resolution import get_game_geometry, get_capture_area

try:
    from config import TEMPLATES_DIR, ROIS, FACE_OFFSET, REFERENCE_WIDTH, AppStatus
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from config import TEMPLATES_DIR, ROIS, FACE_OFFSET, REFERENCE_WIDTH, AppStatus

logger = logging.getLogger("Worker")

class MatcherWorker(QThread):
    # --- Signals ---
    # 매칭 결과: (index, text, score, matched, priority)
    match_signal = pyqtSignal(int, str, float, bool, int)
    # 초기화 신호
    reset_signal = pyqtSignal()
    # 상태 메시지: (StatusEnum, Message)
    status_signal = pyqtSignal(AppStatus, str)
    # 디버그 정보: (index, text, score)
    debug_signal = pyqtSignal(int, str, float)
    # 로딩 완료 신호
    initial_load_finished = pyqtSignal()
    
    geometry_signal = pyqtSignal(dict)

    def __init__(self, build_file: str):
        super().__init__()
        self.build_file = build_file
        self.build_loader: Optional[BuildLoader] = None
        self.running = True
        self.paused = True

    def update_build(self, new_build_file: str):
        """빌드 파일이 변경되었을 때 호출"""
        self.build_file = new_build_file
        try:
            self.build_loader = BuildLoader(self.build_file)
            logger.info(f"빌드 파일 변경됨: {new_build_file}")
            self.status_signal.emit(AppStatus.IDLE, f"빌드 변경됨: {new_build_file}")
        except Exception as e:
            logger.error(f"빌드 로드 실패: {e}")
            self.status_signal.emit(AppStatus.ERROR, "빌드 로드 실패")

    def set_paused(self, paused: bool):
        """일시정지 상태 제어"""
        self.paused = paused
        if self.paused:
            self.status_signal.emit(AppStatus.PAUSED, "일시정지됨")
            self.reset_signal.emit()
            logger.debug("매칭 일시정지")
        else:
            self.status_signal.emit(AppStatus.RUNNING, "실행중")
            logger.debug("매칭 재개")

    def run(self):
        """메인 실행 루프"""
        logger.info("Worker 스레드 시작")
        self.status_signal.emit(AppStatus.LOADING, "리소스 로딩 중...")
        
        # 1. 빌드 및 템플릿 로드
        try:
            self.build_loader = BuildLoader(self.build_file)
            # [변경] TEMPLATE_FOLDER -> TEMPLATES_DIR 사용
            face_templates, skill_templates = load_templates(TEMPLATES_DIR)
        except Exception as e:
            logger.critical(f"초기화 중 치명적 오류: {e}")
            self.status_signal.emit(AppStatus.ERROR, f"초기화 오류: {e}")
            return

        if not face_templates:
            logger.error("얼굴 템플릿 로드 실패 (데이터 없음)")
            self.status_signal.emit(AppStatus.ERROR, "오류: 템플릿 로드 실패")
            return
        
        logger.info(f"리소스 로드 완료 (Face: {len(face_templates)}, Skill: {len(skill_templates)})")
        self.status_signal.emit(AppStatus.RUNNING, "실행중")
        self.initial_load_finished.emit()

        # 2. 감시 루프 시작
        with mss.mss() as sct:
            while self.running:
                if self.paused:
                    time.sleep(0.5)
                    continue

                try:
                    # 게임 창 위치 찾기
                    geo = get_game_geometry()
                    
                    if not geo:
                        self.status_signal.emit(AppStatus.IDLE, "게임 찾는 중...")
                        self.reset_signal.emit()
                        time.sleep(1)
                        continue

                    # [★핵심 수정 유지] 찾은 좌표를 오버레이로 전송
                    self.geometry_signal.emit(geo) 
                    self.status_signal.emit(AppStatus.RUNNING, "실행중")

                    # 화면 스캔 및 인식 처리
                    self.process_rois(sct, geo, face_templates, skill_templates)

                except Exception as e:
                    logger.error(f"메인 루프 에러: {e}")
                    self.status_signal.emit(AppStatus.ERROR, "시스템 오류 발생")
                    time.sleep(1)

                time.sleep(0.1)

    def process_rois(self, sct, geo: dict, face_templates: dict, skill_templates: dict):
        """모든 ROI(감시 영역)를 순회하며 인식 수행"""
        if geo["w"] == 0: return
        scale_factor = REFERENCE_WIDTH / geo["w"]

        for i, roi in enumerate(ROIS):
            # 1단계: 얼굴 인식 시도
            detected_char, diff = self.detect_face(sct, geo, roi, face_templates, scale_factor)
            
            # 디버그 정보 전송
            debug_text = f"[FACE]{detected_char}" if detected_char else "No Face"
            self.debug_signal.emit(i, debug_text, 1.0 - diff)

            # 매칭 임계값 (0.15 diff = 85% 일치)
            if detected_char and diff <= 0.15:
                # 얼굴을 찾았으면 -> 2단계: 스킬 인식 시도
                if detected_char not in skill_templates:
                    # 스킬 템플릿이 없는 캐릭터인 경우 (얼굴만 매칭하고 종료)
                    self.match_signal.emit(i, f"{detected_char}", 1.0 - diff, True, 0)
                    continue

                self.detect_skill(sct, geo, roi, detected_char, skill_templates, scale_factor, i)
            else:
                # 얼굴 인식 실패 시 초기화
                self.match_signal.emit(i, "", 0.0, False, 0)

    def detect_face(self, sct, geo: dict, roi: dict, face_templates: dict, scale_factor: float) -> Tuple[Optional[str], float]:
        """얼굴 인식 로직"""
        face_area = get_capture_area(geo, roi, FACE_OFFSET)
        
        # 영역 유효성 검사
        if face_area["left"] < 0 or face_area["top"] < 0 or face_area["width"] <= 0:
            return None, 1.0

        try:
            img_np = np.array(sct.grab(face_area))
        except Exception:
            return None, 1.0

        # 해상도 보정 (게임 창 크기에 맞춰 리사이징)
        if scale_factor != 1.0:
            img_np = cv2.resize(img_np, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)
        
        detected_char = None
        best_diff = 1.0
        
        # 템플릿 매칭 수행
        for char_name, (face_img, face_mask) in face_templates.items():
            # 마스크를 사용한 템플릿 매칭 (SQDIFF_NORMED: 0에 가까울수록 일치)
            res = cv2.matchTemplate(gray, face_img, cv2.TM_SQDIFF_NORMED, mask=face_mask)
            min_val, _, _, _ = cv2.minMaxLoc(res)
            
            if min_val < best_diff:
                best_diff = min_val
                detected_char = char_name
                
        return detected_char, best_diff

    def detect_skill(self, sct, geo: dict, roi: dict, char_name: str, skill_templates: dict, scale_factor: float, index: int):
        """스킬 아이콘 인식 로직"""
        card_area = get_capture_area(geo, roi, None)
        
        try:
            img_np = np.array(sct.grab(card_area))
        except Exception:
            return

        if scale_factor != 1.0:
            img_np = cv2.resize(img_np, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)

        best_score = 0
        best_filename = ""

        # 해당 캐릭터의 스킬들만 순회
        for filename, skill_img in skill_templates[char_name].items():
            # 일반 템플릿 매칭 (CCOEFF_NORMED: 1에 가까울수록 일치)
            res = cv2.matchTemplate(gray, skill_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            
            if max_val > best_score:
                best_score = max_val
                best_filename = filename

        self.debug_signal.emit(index, best_filename, best_score)

        # 스킬 매칭 임계값 (75% 이상)
        if best_score >= 0.75:
            # 빌드 로더에서 우선순위 가져오기
            priority = 0
            if self.build_loader:
                priority = self.build_loader.get_priority(char_name, best_filename)
            
            self.match_signal.emit(index, best_filename, best_score, True, priority)
        else:
            # 얼굴은 맞는데 스킬을 못 찾은 경우 (캐릭터 이름만 표시)
            self.match_signal.emit(index, f"{char_name} (?)", 0.0, True, 0)

    def stop(self):
        """스레드 안전 종료"""
        self.running = False
        self.quit()
        self.wait(2000)