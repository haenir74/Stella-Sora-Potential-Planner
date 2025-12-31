import ctypes
from ctypes import wintypes
import pygetwindow as gw
from config import TARGET_GAME_TITLE

# WinAPI 구조체 정의 (내부용)
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

last_error_msg = ""
def log_once(msg):
    """이전과 같은 메시지면 출력하지 않음"""
    global last_error_msg
    if msg != last_error_msg:
        print(f"[DEBUG] {msg}")
        last_error_msg = msg

def get_game_geometry():
    """
    현재 게임 창의 정보를 가져옵니다.
    반환값: 성공 시 {x, y, w, h}, 실패 시 None
    """
    try:
        windows = gw.getWindowsWithTitle(TARGET_GAME_TITLE)
        if not windows:
            log_once(f"창을 찾을 수 없음. 검색어: '{TARGET_GAME_TITLE}'")
            return None
        
        hwnd = windows[0]._hWnd
        
        if ctypes.windll.user32.IsIconic(hwnd):
            return None
        
        # 1. 내부 크기 (Client Area)
        client_rect = RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
        width = client_rect.right - client_rect.left
        height = client_rect.bottom - client_rect.top

        # 2. 화면 상 절대 위치 (Client Origin)
        point = wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
        
        if width == 0 or height == 0: return None
        log_once(f"게임 발견 성공! 위치: {point.x},{point.y} 크기: {width}x{height}")

        return {
            "x": point.x, "y": point.y, # 창의 좌상단 절대 좌표
            "w": width,   "h": height   # 창의 내부 크기
        }
    except Exception as e:
        log_once(f"get_game_geometry 내부 오류: {e}")
        return None

def get_capture_area(geo, roi_ratio, face_offset_ratio=None):
    """
    [핵심 함수] 해상도 정보(geo)와 비율(roi_ratio)을 받아
    mss 캡처용 절대 좌표 {top, left, width, height}를 반환합니다.
    """
    # 1. ROI 기본 영역 계산
    roi_x = int(geo["w"] * roi_ratio["x"])
    roi_y = int(geo["h"] * roi_ratio["y"])
    # 2. 오프셋(얼굴 등)이 있다면 적용
    if face_offset_ratio:
        offset_x = int(geo["w"] * face_offset_ratio["x"])
        offset_y = int(geo["h"] * face_offset_ratio["y"])
        offset_w = int(geo["w"] * face_offset_ratio["w"])
        offset_h = int(geo["h"] * face_offset_ratio["h"])
        
        final_x = roi_x + offset_x
        final_y = roi_y + offset_y
        final_w = offset_w
        final_h = offset_h
    else:
        # 오프셋이 없으면 ROI 자체 크기 사용
        final_x = roi_x
        final_y = roi_y
        final_w = int(geo["w"] * roi_ratio["w"])
        final_h = int(geo["h"] * roi_ratio["h"])

    # 3. mss 포맷으로 반환 (모니터 절대 좌표 = 창 위치 + 내부 좌표)
    return {
        "top": geo["y"] + final_y,
        "left": geo["x"] + final_x,
        "width": final_w,
        "height": final_h
    }