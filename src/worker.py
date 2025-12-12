import time
import cv2
import mss
import numpy as np
import pygetwindow as gw
import ctypes
from ctypes import wintypes
from PyQt5.QtCore import QThread, pyqtSignal

# 모듈 임포트
from src.load_image import load_templates
from src.load_build import BuildLoader
from config import TARGET_GAME_TITLE, TEMPLATE_FOLDER, ROIS, FACE_OFFSET,  REFERENCE_WIDTH, REFERENCE_HEIGHT, AppStatus
from src.load_resolution import get_game_geometry, get_capture_area

class MatcherWorker(QThread):
    match_signal = pyqtSignal(int, str, float, bool, int)
    reset_signal = pyqtSignal()
    status_signal = pyqtSignal(AppStatus, str)

    # 디버깅 정보 전송용 시그널 (인덱스, 파일명, 점수)
    debug_signal = pyqtSignal(int, str, float)

    initial_load_finished = pyqtSignal()

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

    def get_client_screen_pos(self, hwnd):
        point = wintypes.POINT()
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
        return point.x, point.y

    def get_active_window_title(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except:
            return ""
        
    def set_paused(self, paused):
        self.paused = paused
        if self.paused:
            self.status_signal.emit(AppStatus.PAUSED, "일시정지됨")
            self.reset_signal.emit() # 정지 시 화면의 박스 제거
        else:
            self.status_signal.emit(AppStatus.RUNNING, "실행중")

    def run(self):
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

                geo = get_game_geometry()
                
                if not geo:
                    self.status_signal.emit(AppStatus.IDLE, "게임 찾는 중...")
                    self.reset_signal.emit()
                    time.sleep(1)
                    continue
                else:
                    self.status_signal.emit(AppStatus.RUNNING, "실행중")

                scale_factor = REFERENCE_WIDTH / geo["w"]

                try:
                    for i, roi in enumerate(ROIS):
                        # 1단계: 얼굴 인식
                        face_area = get_capture_area(geo, roi, FACE_OFFSET)
                        
                        if face_area["left"] < 0 or face_area["top"] < 0: continue

                        frame_face = np.array(sct.grab(face_area))

                        if scale_factor != 1.0:
                            frame_face = cv2.resize(frame_face, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)

                        gray_face = cv2.cvtColor(frame_face, cv2.COLOR_BGRA2GRAY)
                        
                        detected_char = None
                        best_diff = 1.0
                        
                        # 얼굴 매칭
                        for char_name, (face_img, face_mask) in face_templates.items():
                            res = cv2.matchTemplate(gray_face, face_img, cv2.TM_SQDIFF_NORMED, mask=face_mask)
                            min_val, _, _, _ = cv2.minMaxLoc(res)
                            
                            if min_val < best_diff:
                                best_diff = min_val
                                detected_char = char_name

                        similarity = 1.0 - best_diff
                        self.debug_signal.emit(i, f"[FACE]{detected_char}", similarity)

                        if detected_char and best_diff <= 0.15:
                            if detected_char not in skill_templates:
                                self.match_signal.emit(i, f"{detected_char}", 1.0-best_diff, True, 0)
                                continue

                            # 2단계: 스킬 인식
                            card_area = get_capture_area(geo, roi, None)
                            
                            frame_card = np.array(sct.grab(card_area))

                            if scale_factor != 1.0:
                                frame_card = cv2.resize(frame_card, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)

                            gray_card = cv2.cvtColor(frame_card, cv2.COLOR_BGRA2GRAY)

                            best_skill_score = 0
                            best_skill_filename = ""

                            # 스킬 매칭
                            for filename, skill_img in skill_templates[detected_char].items():
                                res = cv2.matchTemplate(gray_card, skill_img, cv2.TM_CCOEFF_NORMED)
                                _, max_val, _, _ = cv2.minMaxLoc(res)
                                
                                if max_val > best_skill_score:
                                    best_skill_score = max_val
                                    best_skill_filename = filename

                            self.debug_signal.emit(i, best_skill_filename, best_skill_score)

                            if best_skill_score >= 0.75:
                                priority = self.build_loader.get_priority(detected_char, best_skill_filename)
                                self.match_signal.emit(i, best_skill_filename, best_skill_score, True, priority)
                            else:
                                self.match_signal.emit(i, f"{detected_char} (?)", 1.0-best_diff, True, 0)
                        else:
                            self.debug_signal.emit(i, "No Face", 0.0)
                            self.match_signal.emit(i, "", 0.0, False, 0)

                    time.sleep(0.1)

                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(1)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()