import time
import cv2
import mss
import numpy as np
import ctypes
from ctypes import wintypes
from PyQt5.QtCore import QThread, pyqtSignal

# 모듈 임포트
from src.load_image import load_templates
from src.load_build import BuildLoader
from config import TEMPLATE_FOLDER, ROIS, FACE_OFFSET, REFERENCE_WIDTH, AppStatus
from src.load_resolution import get_game_geometry, get_capture_area

class MatcherWorker(QThread):
    # 기존 시그널들
    match_signal = pyqtSignal(int, str, float, bool, int)
    reset_signal = pyqtSignal()
    status_signal = pyqtSignal(AppStatus, str)
    debug_signal = pyqtSignal(int, str, float)
    initial_load_finished = pyqtSignal()
    
    # [★핵심 수정] 이 줄이 없어서 에러가 난 것입니다. 꼭 포함되어야 합니다!
    geometry_signal = pyqtSignal(dict)

    def __init__(self, build_file):
        super().__init__()
        self.build_file = build_file
        self.build_loader = None
        self.running = True
        self.paused = True

    def update_build(self, new_build_file):
        self.build_file = new_build_file
        self.build_loader = BuildLoader(self.build_file)
        self.status_signal.emit(AppStatus.IDLE, f"빌드 변경됨: {new_build_file}")

    def set_paused(self, paused):
        self.paused = paused
        if self.paused:
            self.status_signal.emit(AppStatus.PAUSED, "일시정지됨")
            self.reset_signal.emit()
        else:
            self.status_signal.emit(AppStatus.RUNNING, "실행중")

    def run(self):
        """메인 실행 루프"""
        self.status_signal.emit(AppStatus.LOADING, "리소스 로딩 중...")
        self.build_loader = BuildLoader(self.build_file)
        
        face_templates, skill_templates = load_templates(TEMPLATE_FOLDER)
        if not face_templates:
            self.status_signal.emit(AppStatus.ERROR, "오류: 템플릿 로드 실패")
            return
        
        self.status_signal.emit(AppStatus.RUNNING, "실행중")
        self.initial_load_finished.emit()

        with mss.mss() as sct:
            while self.running:
                if self.paused:
                    time.sleep(0.5)
                    continue

                # 1. 게임 창 위치 찾기
                geo = get_game_geometry()
                
                if not geo:
                    self.status_signal.emit(AppStatus.IDLE, "게임 찾는 중...")
                    self.reset_signal.emit()
                    time.sleep(1)
                    continue

                # [★핵심 수정] 찾은 좌표를 오버레이로 전송
                self.geometry_signal.emit(geo) 
                self.status_signal.emit(AppStatus.RUNNING, "실행중")

                # 2. 화면 스캔 및 인식 처리
                self.process_rois(sct, geo, face_templates, skill_templates)

                time.sleep(0.1)

    def process_rois(self, sct, geo, face_templates, skill_templates):
        """모든 ROI(감시 영역)를 순회하며 인식 수행"""
        scale_factor = REFERENCE_WIDTH / geo["w"]

        for i, roi in enumerate(ROIS):
            # 1단계: 얼굴 인식 시도
            detected_char, diff = self.detect_face(sct, geo, roi, face_templates, scale_factor)
            
            self.debug_signal.emit(i, f"[FACE]{detected_char}" if detected_char else "No Face", 1.0 - diff)

            if detected_char and diff <= 0.15:
                # 얼굴을 찾았으면 -> 2단계: 스킬 인식 시도
                if detected_char not in skill_templates:
                    self.match_signal.emit(i, f"{detected_char}", 1.0 - diff, True, 0)
                    continue

                self.detect_skill(sct, geo, roi, detected_char, skill_templates, scale_factor, i)
            else:
                self.match_signal.emit(i, "", 0.0, False, 0)

    def detect_face(self, sct, geo, roi, face_templates, scale_factor):
        """얼굴 인식 로직"""
        face_area = get_capture_area(geo, roi, FACE_OFFSET)
        if face_area["left"] < 0 or face_area["top"] < 0:
            return None, 1.0

        try:
            frame = np.array(sct.grab(face_area))
        except:
            return None, 1.0

        if scale_factor != 1.0:
            frame = cv2.resize(frame, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
        
        detected_char = None
        best_diff = 1.0
        
        for char_name, (face_img, face_mask) in face_templates.items():
            res = cv2.matchTemplate(gray, face_img, cv2.TM_SQDIFF_NORMED, mask=face_mask)
            min_val, _, _, _ = cv2.minMaxLoc(res)
            
            if min_val < best_diff:
                best_diff = min_val
                detected_char = char_name
                
        return detected_char, best_diff

    def detect_skill(self, sct, geo, roi, char_name, skill_templates, scale_factor, index):
        """스킬 아이콘 인식 로직"""
        card_area = get_capture_area(geo, roi, None)
        try:
            frame = np.array(sct.grab(card_area))
        except:
            return

        if scale_factor != 1.0:
            frame = cv2.resize(frame, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)

        best_score = 0
        best_filename = ""

        for filename, skill_img in skill_templates[char_name].items():
            res = cv2.matchTemplate(gray, skill_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            
            if max_val > best_score:
                best_score = max_val
                best_filename = filename

        self.debug_signal.emit(index, best_filename, best_score)

        if best_score >= 0.75:
            priority = self.build_loader.get_priority(char_name, best_filename)
            self.match_signal.emit(index, best_filename, best_score, True, priority)
        else:
            self.match_signal.emit(index, f"{char_name} (?)", 0.0, True, 0)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()