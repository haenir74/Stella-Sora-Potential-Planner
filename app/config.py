import os
import sys
import logging
from pathlib import Path
from enum import Enum, auto

# ------------------------------------------------------
# 1. 로깅 설정 (프로젝트 전역 공통)
# ------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Config")

# ------------------------------------------------------
# 2. 프로젝트 상수 및 버전 정보
# ------------------------------------------------------
TARGET_GAME_TITLE = "StellaSora"
__version__ = "1.0.1"

# 데이터 소스 URL
REPO_BASE_URL = "https://raw.githubusercontent.com/JforPlay/sstoy/refs/heads/main/public/data"
CHARACTER_DB_URL = f"{REPO_BASE_URL}/Character.json"
POTENTIAL_DB_URL = f"{REPO_BASE_URL}/Potential.json"
CHAR_NAME_DB_URL = f"{REPO_BASE_URL}/EN/Character.json"

# 기본 빌드 파일명
DEFAULT_BUILD_FILE = "example_build.json"

# [해상도 및 감시 영역 설정]
REFERENCE_WIDTH = 1280
REFERENCE_HEIGHT = 720
ROIS = [
    {"x": 0.16016, "y": 0.20139, "w": 0.14453, "h": 0.34722},
    {"x": 0.42969, "y": 0.20139, "w": 0.14453, "h": 0.34722},
    {"x": 0.69922, "y": 0.20139, "w": 0.14453, "h": 0.34722}
]
FACE_OFFSET = {"x": -0.05078, "y": -0.02083, "w": 0.05569, "h": 0.16278}

# ------------------------------------------------------
# 3. 경로 설정
# ------------------------------------------------------
# __file__: 현재 파일(config.py)의 절대 경로
# .parent: 이 파일이 있는 디렉토리 (app/)
if getattr(sys, 'frozen', False):
    # [빌드 환경] 실행 파일(.exe)이 있는 폴더를 기준(APP_DIR)으로 잡음
    APP_DIR = Path(sys.executable).parent
else:
    # [개발 환경] config.py 파일이 있는 폴더를 기준(APP_DIR)으로 잡음
    APP_DIR = Path(__file__).resolve().parent

# 프로젝트 루트 (app/ 상위 폴더)
PROJECT_ROOT = APP_DIR.parent

# 리소스 디렉토리 정의
RESOURCES_DIR = APP_DIR / "resources"
TEMPLATES_DIR = RESOURCES_DIR / "templates"
PRESETS_DIR = RESOURCES_DIR / "presets"

# 세부 리소스 경로
ICONS_DIR = TEMPLATES_DIR / "icons"
POTENTIALS_DIR = TEMPLATES_DIR / "potentials"

# ------------------------------------------------------
# 4. 유틸리티 함수: 에러 핸들링 포함
# ------------------------------------------------------
def get_resource_path(relative_path: str) -> Path:
    """
    resources 폴더 내의 파일 절대 경로를 반환합니다.
    파일이 존재하지 않을 경우 에러를 발생시켜 디버깅을 돕습니다.
    """
    # 문자열 경로를 Path 객체로 변환하여 결합
    target_path = RESOURCES_DIR / relative_path
    
    if not target_path.exists():
        error_msg = f"❌ 리소스 파일을 찾을 수 없습니다: {target_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
        
    return target_path

def check_essential_directories():
    """
    앱 실행 초기 단계에서 필수 폴더가 존재하는지 검증합니다.
    """
    required_dirs = {
        "App Root": APP_DIR,
        "Resources": RESOURCES_DIR,
        "Templates": TEMPLATES_DIR,
        "Presets": PRESETS_DIR,
        "Icons": ICONS_DIR,
        "Potentials": POTENTIALS_DIR,
    }
    
    missing_dirs = []
    for name, path in required_dirs.items():
        if not path.exists():
            missing_dirs.append(f"- {name}: {path}")
    
    if missing_dirs:
        error_msg = "❌ 치명적 오류: 다음 필수 디렉토리가 누락되었습니다:\n" + "\n".join(missing_dirs)
        logger.critical(error_msg)
        raise FileNotFoundError(error_msg)
    
    logger.info(f"✅ 경로 시스템 정상 (Base: {APP_DIR})")

# [GUI 상태 정의]
class AppStatus(Enum):
    LOADING = auto()    # 로딩 중
    IDLE = auto()       # 대기 중 (게임을 못 찾음)
    RUNNING = auto()    # 감시 중 (정상 작동)
    PAUSED = auto()     # 일시정지
    ERROR = auto()      # 오류 발생