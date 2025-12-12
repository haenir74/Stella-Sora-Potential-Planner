import pygetwindow as gw
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

# 설정 임포트
from config import TARGET_GAME_TITLE, ROIS, FACE_OFFSET
from src.load_resolution import get_game_geometry, get_capture_area

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.matches = {}
        self.is_visible = True
        
        self.debug_info = {}
        self.face_debug_info = {}
        self.debug_mode = False
        
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

    def set_visibility(self, visible):
        self.is_visible = visible
        self.repaint()

    def set_debug_mode(self, enabled):
        self.debug_mode = enabled
        self.repaint() # 상태 바뀌면 즉시 다시 그리기

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

        geo = get_game_geometry()
        if not geo: return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for i, roi in enumerate(ROIS):
            # -----------------------------------------------------------
            # [디버깅용] 항상 표시되는 인식 범위 박스
            # -----------------------------------------------------------
            if self.debug_mode:
                # 얼굴 인식 범위 (노란색 점선)
                face_area = get_capture_area(geo, roi, FACE_OFFSET)
                painter.setPen(QPen(QColor(255, 255, 0, 150), 1, Qt.DotLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(
                    face_area["left"], face_area["top"], 
                    face_area["width"], face_area["height"]
                )

                # 카드 인식 범위 (하얀색 점선)
                card_area = get_capture_area(geo, roi, None)
                painter.setPen(QPen(QColor(255, 255, 255, 80), 1, Qt.DotLine))
                painter.drawRect(
                    card_area["left"], card_area["top"],
                    card_area["width"], card_area["height"]
                )

            # -------------------------------------------------------
            # 1. 얼굴 디버그 정보 그리기 (노란색)
            # -------------------------------------------------------
            if self.debug_mode:
                if i in self.face_debug_info:
                    fname, score = self.face_debug_info[i]
                    
                    face_area = get_capture_area(geo, roi, FACE_OFFSET)
                    fx, fy = face_area["left"], face_area["top"]
                    fw, fh = face_area["width"], face_area["height"]

                    text = f"{fname}\n({score:.2f})"

                    # 위치: 얼굴 박스 위쪽 (또는 안쪽 상단)
                    painter.setBrush(QColor(0, 0, 0, 200))
                    painter.setPen(Qt.NoPen)
                    painter.drawRect(fx, fy - 40, fw, 40) # 박스 바로 위에 그림

                    painter.setPen(QColor(255, 255, 0)) # 노란색 글씨
                    painter.setFont(QFont("Arial", 9, QFont.Bold))
                    painter.drawText(fx, fy - 40, fw, 40, Qt.AlignCenter, text)
                    
            # -----------------------------------------------------------
            # [디버깅용] 잠재력 디버그 표시
            # -----------------------------------------------------------
            if self.debug_mode and (i in self.debug_info):
                # 여기서도 card_area가 필요하므로 확실하게 계산
                card_area = get_capture_area(geo, roi, None)
                x, y = card_area["left"], card_area["top"]
                w, h = card_area["width"], card_area["height"]

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
                
                if priority == 3:
                    box_color = QColor(255, 165, 0) # Gold
                    line_width = 5
                    label_text = "★ ESSENTIAL ★"
                elif priority == 2:
                    box_color = QColor(255, 0, 255) # Magenta
                    line_width = 3
                    label_text = "Lv.6 RECOMMEND"
                elif priority == 1:
                    box_color = QColor(0, 255, 0)   # Green
                    line_width = 2
                    label_text = "Lv.1 RECOMMEND"
                else:
                    box_color = QColor(200, 200, 200, 50)
                    line_width = 1
                    label_text = ""

                if priority > 0:
                    # 디버그 모드가 꺼져있을 때를 대비해 여기서 card_area를 다시 계산합니다.
                    card_area = get_capture_area(geo, roi, None)
                    
                    abs_x, abs_y = card_area["left"], card_area["top"]
                    abs_w, abs_h = card_area["width"], card_area["height"]

                    painter.setBrush(QColor(0, 0, 0, 180))
                    painter.setPen(Qt.NoPen)
                    painter.drawRect(abs_x, abs_y - 30, 160, 30)

                    painter.setFont(QFont("Arial", 11, QFont.Bold))
                    painter.setPen(box_color)
                    painter.drawText(abs_x + 10, abs_y - 12, label_text)

                painter.setBrush(Qt.NoBrush)