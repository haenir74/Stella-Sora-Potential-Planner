import ctypes
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

# 설정 임포트
from config import ROIS, FACE_OFFSET
from src.load_resolution import get_capture_area

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.matches = {}
        self.is_visible = True
        
        self.debug_info = {}
        self.face_debug_info = {}
        self.debug_mode = False

        # [최적화] 게임 창 위치 정보를 캐싱할 변수
        self.cached_geo = None 
        
        # 윈도우 설정 (투명, 클릭 통과, 최상위)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        hwnd = self.winId()
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020

        style = ctypes.windll.user32.GetWindowLongW(int(hwnd), GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(int(hwnd), GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)

        screen_rect = QApplication.desktop().screenGeometry()
        self.setGeometry(0, 0, screen_rect.width(), screen_rect.height())

    # [NEW] Worker가 보내준 게임 위치 정보를 받아서 저장
    def update_geometry(self, geo):
        self.cached_geo = geo
        self.repaint() # 위치가 업데이트되었으니 다시 그리기

    def set_visibility(self, visible):
        self.is_visible = visible
        self.repaint()

    def set_debug_mode(self, enabled):
        self.debug_mode = enabled
        self.repaint()

    def update_result(self, index, filename, score, matched, priority):
        if matched:
            self.matches[index] = (filename, score, priority)
        else:
            if index in self.matches:
                del self.matches[index]
        self.repaint()

    def update_debug_info(self, index, text, score):
        if text.startswith("[FACE]"):
            real_name = text.replace("[FACE]", "")
            self.face_debug_info[index] = (real_name, score)
        else:
            self.debug_info[index] = (text, score)

    def clear_all(self):
        self.matches.clear()
        self.debug_info.clear()
        self.face_debug_info.clear()
        self.repaint()

    def paintEvent(self, event):
        if not self.is_visible: return

        # [최적화] 매번 계산하지 않고, Worker가 알려준 cached_geo 사용
        geo = self.cached_geo
        if not geo: return 

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for i, roi in enumerate(ROIS):
            # -----------------------------------------------------------
            # [디버깅용] 인식 범위 박스
            # -----------------------------------------------------------
            if self.debug_mode:
                face_area = get_capture_area(geo, roi, FACE_OFFSET)
                painter.setPen(QPen(QColor(255, 255, 0, 150), 1, Qt.DotLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(
                    face_area["left"], face_area["top"], 
                    face_area["width"], face_area["height"]
                )

                card_area = get_capture_area(geo, roi, None)
                painter.setPen(QPen(QColor(255, 255, 255, 80), 1, Qt.DotLine))
                painter.drawRect(
                    card_area["left"], card_area["top"],
                    card_area["width"], card_area["height"]
                )

            # -------------------------------------------------------
            # 1. 얼굴 디버그 정보
            # -------------------------------------------------------
            if self.debug_mode:
                if i in self.face_debug_info:
                    fname, score = self.face_debug_info[i]
                    face_area = get_capture_area(geo, roi, FACE_OFFSET)
                    fx, fy = face_area["left"], face_area["top"]
                    fw = face_area["width"]
                    text = f"{fname}\n({score:.2f})"

                    painter.setBrush(QColor(0, 0, 0, 200))
                    painter.setPen(Qt.NoPen)
                    painter.drawRect(fx, fy - 40, fw, 40)

                    painter.setPen(QColor(255, 255, 0))
                    painter.setFont(QFont("Arial", 9, QFont.Bold))
                    painter.drawText(fx, fy - 40, fw, 40, Qt.AlignCenter, text)
                    
            # -----------------------------------------------------------
            # [디버깅용] 잠재력 디버그 표시
            # -----------------------------------------------------------
            if self.debug_mode and (i in self.debug_info):
                card_area = get_capture_area(geo, roi, None)
                x, y, w, h = card_area["left"], card_area["top"], card_area["width"], card_area["height"]
                fname, score = self.debug_info[i]
                debug_text = f"{fname}\n({score:.2f})"
                
                painter.setBrush(QColor(0, 0, 0, 200))
                painter.setPen(Qt.NoPen)
                painter.drawRect(x, y + h + 5, w, 40)

                painter.setPen(QColor(0, 255, 255))
                painter.setFont(QFont("Arial", 9, QFont.Bold))
                painter.drawText(x, y + h + 5, w, 40, Qt.AlignCenter, debug_text)
            
            # -----------------------------------------------------------
            # [결과 표시] 매칭된 카드 하이라이트
            # -----------------------------------------------------------
            if i in self.matches:
                filename, score, priority = self.matches[i]
                
                # [설정] 5단계 등급 정의
                if priority == 5:
                    # [5] 6레벨 필수 -> 주황색/골드
                    box_color = QColor(255, 140, 0) 
                    line_width = 5
                    label_text = "★ Lv.6 ESSENTIAL ★"
                    
                elif priority == 4:
                    # [4] 6레벨 권장 -> 핑크/자주색
                    box_color = QColor(255, 20, 147) 
                    line_width = 4
                    label_text = "Lv.6 RECOMMEND"
                    
                elif priority == 3:
                    # [3] 1레벨 필수 -> 하늘색/Cyan
                    box_color = QColor(0, 255, 255)
                    line_width = 4
                    label_text = "★ Lv.1 ESSENTIAL ★"
                    
                elif priority == 2:
                    # [2] 1레벨 권장 -> 초록색
                    box_color = QColor(50, 205, 50) 
                    line_width = 3
                    label_text = "Lv.1 RECOMMEND"

                elif priority == 1:
                    # [1] 후순위 -> 흰색/회색
                    box_color = QColor(220, 220, 220) 
                    line_width = 2
                    label_text = "WAIT / LATER"
                    
                else:
                    # 0: 미지정 (표시 안 함)
                    box_color = QColor(0, 0, 0, 0)
                    line_width = 0
                    label_text = ""

                # 텍스트 그리기
                if label_text != "":
                    # Worker에서 받은 캐시된 위치 정보 사용
                    card_area = get_capture_area(geo, roi, None)
                    abs_x, abs_y = card_area["left"], card_area["top"]

                    painter.setBrush(QColor(0, 0, 0, 180))
                    painter.setPen(Qt.NoPen)
                    painter.drawRect(abs_x, abs_y - 30, 160, 30)

                    painter.setFont(QFont("Arial", 11, QFont.Bold))
                    painter.setPen(box_color)
                    painter.drawText(abs_x + 10, abs_y - 12, label_text)

                painter.setBrush(Qt.NoBrush)