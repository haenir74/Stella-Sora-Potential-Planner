import cv2
import mss
import numpy as np
import pygetwindow as gw
import time
import os
import datetime
import ctypes
import keyboard 
import sys # [필수] 실행 경로 확인용
from ctypes import wintypes

# ==========================================
# [설정] 게임 창 이름
TARGET_GAME_TITLE = "StellaSora" 

# [경로 설정] 실행 파일(exe) 기준 경로 찾기
if getattr(sys, 'frozen', False):
    # exe로 실행 시
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 파이썬 스크립트로 실행 시
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 저장될 루트 폴더 (exe 옆 'captured_images' 폴더)
SAVE_ROOT = os.path.join(BASE_DIR, "captured_images")

# [설정] 좌표 및 크기
MODES = {
    "icon": {
        "roi": {"x": 143, "y": 137, "w": 65, "h": 65},
        "desc": "ICON MODE (Circular Mask)",
        "save_folder": os.path.join(SAVE_ROOT, "icons"),
        "mask_enabled": True
    },
    "potential": {
        "roi": {"x": 400, "y": 185, "w": 150, "h": 150},
        "desc": "POTENTIAL MODE (Rectangular)",
        "save_folder": os.path.join(SAVE_ROOT, "potentials"),
        "mask_enabled": False
    }
}

# 프리뷰 확대 배율
PREVIEW_SCALE = 4
WINDOW_NAME = "Capture Tool"
# ==========================================

ctypes.windll.user32.SetProcessDPIAware()

# 폴더 생성
print(f"[시스템] 저장 경로 초기화: {SAVE_ROOT}")
for mode in MODES.values():
    if not os.path.exists(mode["save_folder"]):
        os.makedirs(mode["save_folder"])

# ---------------------------------------------------------
# [기능] 스마트 리셋 (폴더 스캔 함수)
# ---------------------------------------------------------
counters = {"main": 1, "sub": 1}

def scan_and_update_counters(folder):
    """폴더를 읽어서 다음 번호를 자동으로 찾습니다."""
    print(f"\n>>> [시스템] '{os.path.basename(folder)}' 폴더 스캔 중...")
    for prefix in ["main", "sub"]:
        count = 1
        while True:
            filename = f"{prefix}_{count:02d}.png"
            path = os.path.join(folder, filename)
            if not os.path.exists(path):
                break 
            count += 1
        counters[prefix] = count
        print(f"  [{prefix}] -> {count:02d}번 설정됨")
    print(">>> 완료.\n")

# 시작 시 1회 실행
scan_and_update_counters(MODES["potential"]["save_folder"])

print(f"--- '{TARGET_GAME_TITLE}' 캡처 도구 ---")
print("[조작법]")
print("  [Tab]   : 모드 변경")
print("  [Space] : (잠재력) Main <-> Sub 변경")
print("  [S]     : 저장 (게임 중 가능)")
print("  [R]     : 리셋 (폴더 재스캔)")
print("  [Q]     : 종료")
print("-------------------------------------------")

def get_client_screen_pos(hwnd):
    point = wintypes.POINT()
    point.x = 0
    point.y = 0
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
    return point.x, point.y

def apply_circular_mask(img):
    h, w = img.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    center = (w // 2, h // 2)
    radius = min(w, h) // 2
    cv2.circle(mask, center, radius, 255, -1)
    masked_img = cv2.bitwise_and(img, img, mask=mask)
    return masked_img

try:
    windows = gw.getWindowsWithTitle(TARGET_GAME_TITLE)
    if not windows:
        print("게임을 찾을 수 없습니다. 게임을 먼저 실행해주세요.")
        os.system("pause")
        sys.exit()
    game_window = windows[0]
    hwnd = game_window._hWnd 
except Exception as e:
    print(f"오류: {e}")
    os.system("pause")
    sys.exit()

# 초기 변수
current_mode_key = "icon" 
potential_prefix = "main"

with mss.mss() as sct:
    while True:
        try:
            if not gw.getWindowsWithTitle(TARGET_GAME_TITLE): break
        except: break

        # 1. 캡처 및 전처리
        mode_data = MODES[current_mode_key]
        roi = mode_data["roi"]
        
        origin_x, origin_y = get_client_screen_pos(hwnd)
        capture_area = {
            "top": origin_y + roi["y"], "left": origin_x + roi["x"],
            "width": roi["w"], "height": roi["h"]
        }

        try:
            img = np.array(sct.grab(capture_area))
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except:
            time.sleep(0.1)
            continue

        if mode_data["mask_enabled"]:
            save_frame = apply_circular_mask(frame)
        else:
            save_frame = frame

        preview_h, preview_w = roi["h"] * PREVIEW_SCALE, roi["w"] * PREVIEW_SCALE
        preview_frame = cv2.resize(save_frame, (preview_w, preview_h), interpolation=cv2.INTER_NEAREST)

        # 2. UI 그리기
        if mode_data["mask_enabled"]:
            cv2.circle(preview_frame, (preview_w//2, preview_h//2), (min(preview_w, preview_h)//2)-2, (0, 255, 0), 2)
        else:
            cv2.rectangle(preview_frame, (0, 0), (preview_w-1, preview_h-1), (0, 255, 0), 2)

        # 텍스트 정보 표시
        info_text = mode_data["desc"]
        if current_mode_key == "potential":
            curr_count = counters[potential_prefix]
            next_file = f"{potential_prefix}_{curr_count:02d}.png"
            
            cv2.putText(preview_frame, f"TYPE: {potential_prefix.upper()}", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(preview_frame, f"Next: {next_file}", (10, 90), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            cv2.putText(preview_frame, f"Time: {timestamp}", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

        cv2.putText(preview_frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow(WINDOW_NAME, preview_frame)
        
        # 3. 키보드 입력 처리
        cv2.waitKey(1)

        try:
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
        except:
            pass

        if keyboard.is_pressed('q'):
            break

        if keyboard.is_pressed('tab'):
            current_mode_key = "potential" if current_mode_key == "icon" else "icon"
            time.sleep(0.2)
            continue

        if keyboard.is_pressed('space'):
            if current_mode_key == "potential":
                potential_prefix = "sub" if potential_prefix == "main" else "main"
                time.sleep(0.2)
            continue

        if keyboard.is_pressed('r'):
            scan_and_update_counters(mode_data["save_folder"])
            time.sleep(0.5)
            continue

        if keyboard.is_pressed('s'):
            if current_mode_key == "potential":
                count = counters[potential_prefix]
                filename = f"{potential_prefix}_{count:02d}.png"
                full_path = f"{mode_data['save_folder']}/{filename}"
                cv2.imwrite(full_path, save_frame)
                print(f" [저장됨] {filename}")
                counters[potential_prefix] += 1
            else:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"icon_{timestamp}.png"
                full_path = f"{mode_data['save_folder']}/{filename}"
                cv2.imwrite(full_path, save_frame)
                print(f" [저장됨] {filename}")
            
            # 저장 피드백
            inverted = cv2.bitwise_not(preview_frame)
            cv2.imshow(WINDOW_NAME, inverted)
            cv2.waitKey(1)
            time.sleep(0.2)

cv2.destroyAllWindows()