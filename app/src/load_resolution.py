import ctypes
import logging
from ctypes import wintypes
from typing import Optional, Dict, Any, Union

import pygetwindow as gw

# ------------------------------------------------------
# 설정 임포트
# ------------------------------------------------------
try:
    from config import TARGET_GAME_TITLE
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from config import TARGET_GAME_TITLE

# 로거 설정
logger = logging.getLogger("Resolution")

# ------------------------------------------------------
# WinAPI 구조체 및 상수 (Internal)
# ------------------------------------------------------
class _RECT(ctypes.Structure):
    """Windows API용 RECT 구조체"""
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

# 중복 로그 방지를 위한 전역 변수
_last_log_msg: Optional[str] = None

def _log_once(msg: str, level: int = logging.DEBUG):
    """
    이전과 동일한 메시지는 출력하지 않는 로깅 함수.
    반복 루프에서 로그 스팸을 방지하기 위해 사용합니다.
    """
    global _last_log_msg
    if msg != _last_log_msg:
        logger.log(level, msg)
        _last_log_msg = msg

# ------------------------------------------------------
# Core Functions
# ------------------------------------------------------
def get_game_geometry() -> Optional[Dict[str, int]]:
    """
    현재 게임 창의 위치와 크기 정보를 가져옵니다.
    
    Returns:
        성공 시: {"x": int, "y": int, "w": int, "h": int}
        실패 시: None
    """
    try:
        # 1. 윈도우 핸들 찾기
        windows = gw.getWindowsWithTitle(TARGET_GAME_TITLE)
        if not windows:
            _log_once(f"창을 찾을 수 없음. 검색어: '{TARGET_GAME_TITLE}'", logging.DEBUG)
            return None
        
        target_window = windows[0]
        hwnd = target_window._hWnd
        
        # 2. 최소화 여부 확인
        if ctypes.windll.user32.IsIconic(hwnd):
            _log_once("게임 창이 최소화되어 있습니다.", logging.DEBUG)
            return None
        
        # 3. 내부 크기 (Client Area) 계산
        #    GetWindowRect는 테두리 포함이므로 GetClientRect 사용
        client_rect = _RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
        width = client_rect.right - client_rect.left
        height = client_rect.bottom - client_rect.top

        # 4. 화면 상 절대 위치 (Client Origin -> Screen Coordinate)
        point = wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
        
        if width <= 0 or height <= 0:
            _log_once("게임 창 크기가 유효하지 않습니다 (0x0).", logging.WARNING)
            return None

        # 성공 시 로그 (최초 1회만)
        _log_once(f"게임 발견 성공! 위치: {point.x},{point.y} 크기: {width}x{height}", logging.INFO)

        return {
            "x": int(point.x), 
            "y": int(point.y), # 창의 클라이언트 영역 좌상단 절대 좌표
            "w": int(width),   
            "h": int(height)   # 창의 내부 크기
        }
        
    except Exception as e:
        _log_once(f"get_game_geometry 내부 오류: {e}", logging.ERROR)
        return None

def get_capture_area(
    geo: Dict[str, int], 
    roi_ratio: Dict[str, float], 
    face_offset_ratio: Optional[Dict[str, float]] = None
) -> Dict[str, int]:
    """
    해상도 정보(geo)와 비율(roi_ratio)을 받아 mss 캡처용 절대 좌표를 계산합니다.
    
    Args:
        geo: get_game_geometry()의 리턴값 (x, y, w, h)
        roi_ratio: config.ROIS에 정의된 비율 정보 (x, y, w, h)
        face_offset_ratio: (선택) 얼굴 영역 오프셋 비율 정보
        
    Returns:
        mss 포맷의 영역 정보: {"top": int, "left": int, "width": int, "height": int}
    """
    # 1. ROI 기본 영역 계산 (상대 좌표)
    roi_x = int(geo["w"] * roi_ratio["x"])
    roi_y = int(geo["h"] * roi_ratio["y"])
    
    final_x: int
    final_y: int
    final_w: int
    final_h: int

    # 2. 오프셋 적용 여부 분기
    if face_offset_ratio:
        # 얼굴 영역 계산 (ROI 기준 상대 위치 적용)
        offset_x = int(geo["w"] * face_offset_ratio["x"])
        offset_y = int(geo["h"] * face_offset_ratio["y"])
        offset_w = int(geo["w"] * face_offset_ratio["w"])
        offset_h = int(geo["h"] * face_offset_ratio["h"])
        
        final_x = roi_x + offset_x
        final_y = roi_y + offset_y
        final_w = offset_w
        final_h = offset_h
    else:
        # 일반 카드 영역 (ROI 자체 크기)
        final_x = roi_x
        final_y = roi_y
        final_w = int(geo["w"] * roi_ratio["w"])
        final_h = int(geo["h"] * roi_ratio["h"])

    # 3. 절대 좌표 변환 (창 위치 + 상대 좌표)
    return {
        "top": geo["y"] + final_y,
        "left": geo["x"] + final_x,
        "width": final_w,
        "height": final_h
    }