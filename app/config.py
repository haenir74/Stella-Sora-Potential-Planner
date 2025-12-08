from enum import Enum, auto

# [버전 정보]
__version__ = "1.0.0"

# [게임 설정]
TARGET_GAME_TITLE = "StellaSora" 
TEMPLATE_FOLDER = "templates"
BUILDS_FOLDER = "builds"
DEFAULT_BUILD_FILE = "example_build.json"

# [감시 영역 설정] (절대 좌표)
# ROIS = [
#     {"x": 215, "y": 170, "w": 165, "h": 200}, # 1번 카드 (왼쪽)
#     {"x": 560, "y": 170, "w": 165, "h": 200}, # 2번 카드 (가운데)
#     {"x": 905, "y": 170, "w": 165, "h": 200}  # 3번 카드 (오른쪽)
# ]

REFERENCE_WIDTH = 1280
REFERENCE_HEIGHT = 720

# [감시 영역 설정] (상대 좌표: 0.0 ~ 1.0)
# 기준 해상도: 1280x720
ROIS = [
    {"x": 0.16016, "y": 0.20139, "w": 0.14453, "h": 0.34722},
    {"x": 0.42969, "y": 0.20139, "w": 0.14453, "h": 0.34722},
    {"x": 0.69922, "y": 0.20139, "w": 0.14453, "h": 0.34722}
]

# [얼굴 인식 영역 설정] (절대 좌표)
# FACE_OFFSET = {"x": -75, "y": -40, "w": 70, "h": 110}

# [얼굴 인식 영역 보정] (상대 좌표)
FACE_OFFSET = {"x": -0.05078, "y": -0.02083, "w": 0.05569, "h": 0.16278}

# [GUI 상태 정의]
class AppStatus(Enum):
    LOADING = auto()    # 로딩 중
    IDLE = auto()       # 대기 중 (게임을 못 찾음)
    RUNNING = auto()    # 감시 중 (정상 작동)
    PAUSED = auto()     # 일시정지
    ERROR = auto()      # 오류 발생