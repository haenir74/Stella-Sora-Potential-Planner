import ctypes
import time
import os

# ==========================================
# [설정] 본인이 확인하고 싶은 게임 이름 일부를 적으세요
TARGET_NAME = "StellaSora"
# ==========================================

def get_active_window_title():
    """
    Windows API를 사용하여 현재 맨 앞(Active)에 있는 창의 제목을 가져옵니다.
    """
    try:
        # 1. 현재 포그라운드(맨 앞) 창의 핸들(ID)을 가져옴
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        
        # 2. 제목의 길이를 알아냄
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        
        # 3. 버퍼 생성 및 제목 복사
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        
        return buff.value
    except Exception as e:
        return f"Error: {e}"

def main():
    print("--- 활성 창 감지 테스트 도구 ---")
    print(f"타겟 이름: '{TARGET_NAME}'")
    print("종료하려면 Ctrl+C를 누르세요.\n")

    last_title = ""

    while True:
        # 현재 활성 창 제목 가져오기
        current_title = get_active_window_title()
        
        # 타겟 게임인지 판별
        is_target = TARGET_NAME in current_title if current_title else False
        
        # 상태 메시지 생성
        status = "[게임 감지됨! O]" if is_target else "[다른 작업 중 X]"
        
        # 출력 (보기 편하게 포맷팅)
        # 내용이 달라질 때만 출력하려면 아래 if문 주석을 해제하세요
        # if current_title != last_title:
        print(f"{status} 현재 활성 창: {current_title}")
        
        last_title = current_title
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n테스트를 종료합니다.")