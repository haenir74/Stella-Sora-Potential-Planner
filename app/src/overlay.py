import ctypes
import logging
from typing import Dict, Tuple, Optional, List, Union

from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QPaintEvent

# ------------------------------------------------------
# 설정 및 유틸리티 임포트
# ------------------------------------------------------
try:
    from config import ROIS, FACE_OFFSET
    from src.load_resolution import get_capture_area
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from config import ROIS, FACE_OFFSET
    from src.load_resolution import get_capture_area

logger = logging.getLogger("Overlay")

class OverlayWindow(QWidget):
    # ------------------------------------------------------
    # 상수 및 스타일 정의
    # ------------------------------------------------------
    # 우선순위별 스타일: (테두리 색상, 두께, 라벨 텍스트)
    PRIORITY_STYLES = {
        5: (QColor(255, 140, 0), 5, "★ Lv.6 ESSENTIAL ★"),   # 주황/골드
        4: (QColor(255, 20, 147), 4, "Lv.6 RECOMMEND"),       # 핑크/자주
        3: (QColor(0, 255, 255), 4, "★ Lv.1 ESSENTIAL ★"),   # 시안(Cyan)
        2: (QColor(50, 205, 50), 3, "Lv.1 RECOMMEND"),        # 라임/초록
        1: (QColor(220, 220, 220), 2, "WAIT / LATER"),        # 회색
    }

    def __init__(self):
        super().__init__()
        self.matches: Dict[int, Tuple[str, float, int]] = {}
        self.is_visible: bool = True
        
        self.debug_info: Dict[int, Tuple[str, float]] = {}
        self.face_debug_info: Dict[int, Tuple[str, float]] = {}
        self.debug_mode: bool = False

        # 게임 창 위치 정보 캐싱 (Worker로부터 수신)
        self.cached_geo: Optional[Dict[str, int]] = None 
        
        self._init_window_settings()
        logger.info("오버레이 윈도우 초기화 완료")

    def _init_window_settings(self):
        """윈도우 투명화 및 클릭 통과 설정 (Windows API)"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 전체 화면 크기로 설정
        screen_rect = QApplication.desktop().screenGeometry()
        self.setGeometry(0, 0, screen_rect.width(), screen_rect.height())

        # Windows 확장 스타일 설정 (클릭 통과 핵심)
        try:
            hwnd = self.winId()
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020

            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(int(hwnd), GWL_EXSTYLE)
            user32.SetWindowLongW(int(hwnd), GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        except Exception as e:
            logger.error(f"윈도우 스타일 설정 실패: {e}")

    # ------------------------------------------------------
    # 데이터 업데이트 메서드 (Worker 연결)
    # ------------------------------------------------------
    def update_geometry(self, geo: Dict[str, int]):
        """게임 창의 위치 정보를 업데이트합니다."""
        self.cached_geo = geo
        self.repaint() # 위치 변경 시 즉시 갱신

    def update_result(self, index: int, filename: str, score: float, matched: bool, priority: int):
        """매칭 결과를 업데이트합니다."""
        if matched:
            self.matches[index] = (filename, score, priority)
        else:
            self.matches.pop(index, None)
        self.repaint()

    def update_debug_info(self, index: int, text: str, score: float):
        """디버깅 정보를 업데이트합니다."""
        if text.startswith("[FACE]"):
            real_name = text.replace("[FACE]", "")
            self.face_debug_info[index] = (real_name, score)
        else:
            self.debug_info[index] = (text, score)
        
        # 디버그 모드일 때만 리페인트하여 성능 절약
        if self.debug_mode:
            self.repaint()

    def clear_all(self):
        """모든 표시 정보를 초기화합니다."""
        self.matches.clear()
        self.debug_info.clear()
        self.face_debug_info.clear()
        self.repaint()

    # ------------------------------------------------------
    # 설정 제어
    # ------------------------------------------------------
    def set_visibility(self, visible: bool):
        self.is_visible = visible
        self.repaint()

    def set_debug_mode(self, enabled: bool):
        self.debug_mode = enabled
        self.repaint()

    # ------------------------------------------------------
    # 그리기 로직 (Core)
    # ------------------------------------------------------
    def paintEvent(self, event: QPaintEvent):
        if not self.is_visible:
            return

        # 게임 위치 정보가 없으면 그릴 수 없음
        geo = self.cached_geo
        if not geo:
            return 

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 모든 ROI(감시 영역)에 대해 그리기 수행
            for i, roi in enumerate(ROIS):
                self._draw_roi_visuals(painter, i, roi, geo)

        except Exception as e:
            # 그리기 도중 에러가 나도 앱이 꺼지지 않도록 처리
            logger.error(f"Paint Event 오류: {e}")
        finally:
            painter.end()

    def _draw_roi_visuals(self, painter: QPainter, index: int, roi: Dict[str, float], geo: Dict[str, int]):
        """개별 ROI에 대한 시각적 요소를 그립니다."""
        
        # 1. 디버그 모드: 인식 영역 박스 표시
        if self.debug_mode:
            self._draw_debug_boxes(painter, index, roi, geo)

        # 2. 결과 표시: 매칭된 카드 하이라이트
        if index in self.matches:
            filename, score, priority = self.matches[index]
            self._draw_match_result(painter, roi, geo, priority)

    def _draw_debug_boxes(self, painter: QPainter, index: int, roi: Dict[str, float], geo: Dict[str, int]):
        """(디버그) 얼굴 및 스킬 인식 영역과 텍스트를 그립니다."""
        # A. 얼굴 인식 영역
        face_area = get_capture_area(geo, roi, FACE_OFFSET)
        painter.setPen(QPen(QColor(255, 255, 0, 150), 1, Qt.DotLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(face_area["left"], face_area["top"], face_area["width"], face_area["height"])

        if index in self.face_debug_info:
            fname, score = self.face_debug_info[index]
            self._draw_label(painter, 
                             face_area["left"], face_area["top"] - 40, face_area["width"], 40,
                             f"{fname}\n({score:.2f})", QColor(255, 255, 0))

        # B. 스킬(카드) 인식 영역
        card_area = get_capture_area(geo, roi, None)
        painter.setPen(QPen(QColor(255, 255, 255, 80), 1, Qt.DotLine))
        painter.drawRect(card_area["left"], card_area["top"], card_area["width"], card_area["height"])

        if index in self.debug_info:
            fname, score = self.debug_info[index]
            self._draw_label(painter, 
                             card_area["left"], card_area["top"] + card_area["height"] + 5, card_area["width"], 40,
                             f"{fname}\n({score:.2f})", QColor(0, 255, 255))

    def _draw_match_result(self, painter: QPainter, roi: Dict[str, float], geo: Dict[str, int], priority: int):
        """매칭된 결과(우선순위)에 따라 테두리와 라벨을 그립니다."""
        style = self.PRIORITY_STYLES.get(priority)
        if not style:
            return # 스타일이 정의되지 않은 우선순위(0 등)는 그리지 않음

        box_color, line_width, label_text = style
        card_area = get_capture_area(geo, roi, None)
        x, y = card_area["left"], card_area["top"]

        # 텍스트 배경 및 라벨
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.setPen(Qt.NoPen)
        painter.drawRect(x, y - 30, 160, 30) # 라벨 배경

        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.setPen(box_color)
        painter.drawText(x + 10, y - 12, label_text) # 라벨 텍스트

    def _draw_label(self, painter: QPainter, x: int, y: int, w: int, h: int, text: str, color: QColor):
        """검은 반투명 배경 위에 텍스트를 그리는 헬퍼 함수"""
        painter.setBrush(QColor(0, 0, 0, 200))
        painter.setPen(Qt.NoPen)
        painter.drawRect(x, y, w, h)

        painter.setPen(color)
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        painter.drawText(x, y, w, h, Qt.AlignCenter, text)