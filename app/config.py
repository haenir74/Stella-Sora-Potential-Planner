import os
import sys
from enum import Enum, auto

# [게임 및 버전 정보]
TARGET_GAME_TITLE = "StellaSora"
__version__ = "1.0.0"

# =========================================================
# 실행 환경에 따른 경로 분기 처리
# =========================================================
if getattr(sys, 'frozen', False):
    # 1. PyInstaller로 빌드된 EXE 실행 환경
    # exe 파일이 위치한 폴더를 기준(Root)으로 잡습니다.
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 2. 개발 환경 (Python 실행)
    # 이 파일(config.py)이 있는 폴더(app)를 기준으로 잡습니다.
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 리소스 경로 연결
RESOURCES_DIR = os.path.join(BASE_DIR, "resources")
TEMPLATE_FOLDER = os.path.join(RESOURCES_DIR, "templates")
BUILDS_FOLDER = os.path.join(RESOURCES_DIR, "presets")
DEFAULT_BUILD_FILE = "example_build.json"

REPO_BASE_URL = "https://raw.githubusercontent.com/JforPlay/sstoy/refs/heads/main/public/data"
CHARACTER_DB_URL = f"{REPO_BASE_URL}/Character.json"
POTENTIAL_DB_URL = f"{REPO_BASE_URL}/Potential.json"
CHAR_NAME_DB_URL = f"{REPO_BASE_URL}/EN/Character.json"
# =========================================================

# [감시 영역 설정] (상대 좌표: 0.0 ~ 1.0)
# 기준 해상도: 1280x720
REFERENCE_WIDTH = 1280
REFERENCE_HEIGHT = 720

ROIS = [
    {"x": 0.16016, "y": 0.20139, "w": 0.14453, "h": 0.34722},
    {"x": 0.42969, "y": 0.20139, "w": 0.14453, "h": 0.34722},
    {"x": 0.69922, "y": 0.20139, "w": 0.14453, "h": 0.34722}
]

# [얼굴 인식 영역 보정] (상대 좌표)
FACE_OFFSET = {"x": -0.05078, "y": -0.02083, "w": 0.05569, "h": 0.16278}

# [GUI 상태 정의]
class AppStatus(Enum):
    LOADING = auto()    # 로딩 중
    IDLE = auto()       # 대기 중 (게임을 못 찾음)
    RUNNING = auto()    # 감시 중 (정상 작동)
    PAUSED = auto()     # 일시정지
    ERROR = auto()      # 오류 발생