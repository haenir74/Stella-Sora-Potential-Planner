import logging
import os
import sys
from datetime import datetime

def setup_logging():
    # 1. 로그를 저장할 폴더 생성 (실행 파일 위치 기준 'logs' 폴더)
    # PyInstaller로 빌드된 경우와 일반 실행의 경로 차이를 고려
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        
    log_dir = os.path.join(application_path, "logs")
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 2. 로그 파일명 설정 (날짜별로 파일 분리: log_20240113.txt)
    today = datetime.now().strftime("%Y-%m-%d")
    log_filepath = os.path.join(log_dir, f"log_{today}.txt")

    # 3. 로거 설정
    # DEBUG 레벨 이상을 기록하며, 콘솔과 파일 양쪽에 출력합니다.
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.FileHandler(log_filepath, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )

    # 4. 프로그램이 갑자기 꺼질 때 에러를 로그에 남기는 훅(Hook) 설정
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
    logging.info(f"=== Application Started (Log: {log_filepath}) ===")

# 모듈별로 로거를 가져올 때 사용할 헬퍼 함수
def get_logger(name):
    return logging.getLogger(name)