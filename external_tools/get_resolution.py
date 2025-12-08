# external_tools.py
import ctypes
from ctypes import wintypes
import pygetwindow as gw


# [WinAPI] RECT 구조체 정의
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

class GameGeometry:
    def __init__(self, title):
        self.target_title = title

    def get_geometry(self):
        """
        게임 창의 'Client Area' (테두리 제외한 내부 화면)의 
        절대 좌표(x, y)와 크기(w, h)를 반환합니다.
        """
        try:
            # 1. 윈도우 핸들(HWND) 찾기
            windows = gw.getWindowsWithTitle(self.target_title)
            if not windows:
                return None
            
            # pygetwindow 객체에서 핸들 추출 (비공개 속성 _hWnd 사용)
            win = windows[0]
            hwnd = win._hWnd

            # 2. ClientRect 가져오기 (내부 크기)
            client_rect = RECT()
            ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
            width = client_rect.right - client_rect.left
            height = client_rect.bottom - client_rect.top

            # 3. ClientToScreen (내부 영역의 좌상단 절대 좌표)
            # (0, 0) 포인트가 모니터 상의 어디에 있는지 변환
            point = wintypes.POINT(0, 0)
            ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
            origin_x = point.x
            origin_y = point.y

            return {
                "x": origin_x,
                "y": origin_y,
                "w": width,
                "h": height
            }

        except Exception as e:
            print(f"[external_tools] 윈도우 정보 조회 실패: {e}")
            return None

    def calculate_scale_ratio(self, reference_w=1280, reference_h=720):
        """
        기준 해상도 대비 현재 해상도의 비율(Scale Factor)을 계산합니다.
        예: 기준 1280x720, 현재 1920x1080 -> ratio_x=1.5, ratio_y=1.5
        """
        geo = self.get_geometry()
        if not geo:
            return 1.0, 1.0
        
        current_w = geo["w"]
        current_h = geo["h"]

        ratio_x = current_w / reference_w
        ratio_y = current_h / reference_h
        
        return ratio_x, ratio_y

# --- 테스트 실행 코드 ---
if __name__ == "__main__":
    tool = GameGeometry("StellaSora")
    geometry = tool.get_geometry()
    
    if geometry:
        print(f"=== [{"StellaSora"}] Geometry Info ===")
        print(f"Position (Screen): ({geometry['x']}, {geometry['y']})")
        print(f"Size (Client Area): {geometry['w']} x {geometry['h']}")
        
        # 1600x900 기준 스케일링 테스트
        rx, ry = tool.calculate_scale_ratio(1600, 900)
        print(f"Scale Factor (Ref: 1600x900): x={rx:.2f}, y={ry:.2f}")
    else:
        print("게임을 찾을 수 없습니다.")