import cv2
import mss
import numpy as np
import pygetwindow as gw
import time

# ==========================================
TARGET_GAME_TITLE = "StellaSora"
# ==========================================

print(f"'{TARGET_GAME_TITLE}' 창을 찾는 중...")

try:
    # 1. 게임 창 찾기
    windows = gw.getWindowsWithTitle(TARGET_GAME_TITLE)
    if not windows:
        print("게임을 찾을 수 없습니다.")
        exit()
    
    game_window = windows[0]
    if game_window.isMinimized:
        game_window.restore() # 최소화 되어있으면 복구
        time.sleep(0.5)

    # 2. 게임 화면 캡처
    with mss.mss() as sct:
        capture_area = {
            "top": game_window.top,
            "left": game_window.left,
            "width": game_window.width,
            "height": game_window.height
        }
        img = np.array(sct.grab(capture_area))
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    # 3. ROI 선택 도구 실행 (마우스로 드래그 후 스페이스바 또는 엔터)
    print("\n[안내] 마우스로 세 카드가 포함된 영역을 드래그하세요.")
    print("[안내] 선택 후 'SPACE' 또는 'ENTER'를 누르면 좌표가 출력됩니다.")
    print("[안내] 취소하려면 'c'를 누르세요.")
    
    # cv2.selectROI는 (x, y, w, h)를 반환합니다.
    # x, y는 게임 창 왼쪽 위 모서리가 (0,0)인 상대 좌표입니다.
    roi = cv2.selectROI("ROI Selector", img, showCrosshair=True, fromCenter=False)
    cv2.destroyAllWindows()

    # 4. 결과 출력
    x, y, w, h = roi
    
    if w == 0 or h == 0:
        print("\n영역이 선택되지 않았습니다.")
    else:
        print("\n" + "="*40)
        print(">>> 아래 코드를 main.py의 ROI 설정 부분에 복사하세요! <<<")
        print(f"roi_x = {x}")
        print(f"roi_y = {y}")
        print(f"roi_w = {w}")
        print(f"roi_h = {h}")
        print("="*40)

except Exception as e:
    print(f"에러 발생: {e}")