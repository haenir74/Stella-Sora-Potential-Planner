import sys
import os
import json
import re
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

try:
    from . import decoder
except ImportError:
    import decoder

try:
    from config import (
        CHARACTER_DB_URL, POTENTIAL_DB_URL, CHAR_NAME_DB_URL, 
        PRESETS_DIR
    )
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from config import (
        CHARACTER_DB_URL, POTENTIAL_DB_URL, CHAR_NAME_DB_URL, 
        PRESETS_DIR
    )

# 로거 설정
logger = logging.getLogger("BuildMaker")
class ConverterWorker(QThread):
    log_signal = pyqtSignal(str)       # 로그 메시지
    progress_signal = pyqtSignal(int)  # 진행률 (0~100)
    finished_signal = pyqtSignal(bool, str) # 성공 여부, 결과 메시지

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def fetch_db(self, url: str, name: str) -> Dict[str, Any]:
        """SSToy의 최신 DB(JSON)를 다운로드합니다."""
        self.log_signal.emit(f"📥 {name} 데이터 다운로드 중...")
        try:
            # 타임아웃 설정으로 무한 대기 방지
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"{name} 다운로드 실패: {e}")

    def build_id_mapping(self, db_json: Dict[str, Any]) -> List[int]:
        """DB 키(ID)를 정수 리스트로 변환하여 정렬합니다."""
        if not db_json: return []
        # 키가 문자열 숫자일 수 있으므로 int 변환
        all_ids = [int(k) for k in db_json.keys()]
        return sorted(list(set(all_ids)))

    def get_real_id(self, mapped_idx: int, id_map: List[int]) -> Optional[int]:
        """매핑된 인덱스를 실제 게임 ID로 변환합니다."""
        if 0 < mapped_idx <= len(id_map):
            return id_map[mapped_idx - 1]
        return None

    def get_program_char_key(self, real_id: int, name_db: Dict[str, str]) -> str:
        """프로그램에서 사용하는 캐릭터 키(파일명 기반)를 생성합니다."""
        if not name_db: return f"unknown_{real_id}"
        
        # DB 키 형식 예시: "Character.1042.1" -> "Character.{ID}.1"
        key = f"Character.{real_id}.1"
        english_name = name_db.get(key, f"Unknown_{real_id}")
        
        # 포맷 변환: 소문자화 -> 공백을 언더바로 -> 특수문자 제거
        # 예: "Dark K" -> "dark_k"
        formatted_key = english_name.lower().replace(" ", "_")
        formatted_key = re.sub(r'[^a-z0-9_]', '', formatted_key)
        return formatted_key

    def sanitize_filename(self, name: str) -> str:
        """파일 저장용 안전한 이름으로 변환합니다."""
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def run(self):
        try:
            self.progress_signal.emit(10)

            # 1. 최신 데이터 DB 다운로드 (순차적)
            char_db = self.fetch_db(CHARACTER_DB_URL, "Character")
            self.progress_signal.emit(30)
            
            pot_db = self.fetch_db(POTENTIAL_DB_URL, "Potential")
            self.progress_signal.emit(50)
            
            name_db = self.fetch_db(CHAR_NAME_DB_URL, "Character Name (EN)")
            self.progress_signal.emit(70)

            # 2. 매핑 테이블 생성
            char_map = self.build_id_mapping(char_db)
            pot_map = self.build_id_mapping(pot_db)

            # 3. URL 해독
            self.log_signal.emit("🔓 URL 해독 및 파싱 중...")
            decoded = decoder.decode_url_raw(self.url)
            
            if "error" in decoded:
                raise Exception(decoded['error'])

            build_name = decoded['build_name']
            safe_filename = f"{self.sanitize_filename(build_name)}.json"
            
            # 4. 저장 폴더 확인 (config.PRESETS_DIR 사용)
            if not PRESETS_DIR.exists():
                PRESETS_DIR.mkdir(parents=True, exist_ok=True)
                self.log_signal.emit(f"📂 폴더 생성됨: {PRESETS_DIR}")

            output_path = PRESETS_DIR / safe_filename
            self.log_signal.emit(f"📝 빌드 변환 시작: {build_name}")

            # 5. JSON 구조 생성
            result_json = {
                "build_name": build_name,
                "characters": {}
            }

            raw_chars = decoded['raw_characters']
            positions = ['master', 'assist1', 'assist2']

            for pos in positions:
                if pos not in raw_chars: continue
                
                data = raw_chars[pos]
                
                # ID 매핑
                real_char_id = self.get_real_id(data['mapped_char_idx'], char_map)
                if real_char_id is None:
                    continue

                char_key = self.get_program_char_key(real_char_id, name_db)
                self.log_signal.emit(f"  - [{pos.upper()}] {char_key} (ID:{real_char_id})")
                
                # 잠재력 매핑
                potentials_dict = {}
                for mapped_pot_idx in data['mapped_potentials']:
                    real_pot_id = self.get_real_id(mapped_pot_idx, pot_map)
                    if real_pot_id is None:
                        continue
                    
                    # 마크(우선순위)가 없으면 기본값 2 (Lv.1 권장) 적용
                    priority = data['marks'].get(mapped_pot_idx, 2)
                    potentials_dict[str(real_pot_id)] = priority
                    
                result_json["characters"][char_key] = potentials_dict

            # 6. 파일 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result_json, f, indent=2, ensure_ascii=False)
            
            self.progress_signal.emit(100)
            self.finished_signal.emit(True, f"저장 완료!\n파일: {output_path.name}")

        except Exception as e:
            logger.error(f"변환 작업 실패: {e}")
            self.finished_signal.emit(False, str(e))

class BuildMakerApp(QWidget):
    conversion_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SSToy Build Converter")
        self.resize(500, 450)
        self.worker: Optional[ConverterWorker] = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 타이틀
        title = QLabel("SSToy URL → 빌드 파일 변환기")
        title.setFont(QFont("Malgun Gothic", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 설명
        desc = QLabel("공유받은 URL을 입력하면 프로그램용 빌드 파일로 변환하여\nPresets 폴더에 저장합니다.")
        desc.setStyleSheet("color: #666;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        # URL 입력창
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("https://jforplay.github.io/sstoy/app.html#build=...")
        self.input_url.setMinimumHeight(40)
        layout.addWidget(self.input_url)

        # 변환 버튼
        self.btn_convert = QPushButton("변환 및 저장 (Convert)")
        self.btn_convert.setMinimumHeight(50)
        self.btn_convert.setCursor(Qt.PointingHandCursor)
        self.btn_convert.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                font-size: 14px; 
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.btn_convert.clicked.connect(self.start_conversion)
        layout.addWidget(self.btn_convert)

        # 진행바
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { border: 0px; background-color: #e0e0e0; height: 5px; } QProgressBar::chunk { background-color: #2196F3; }")
        layout.addWidget(self.progress_bar)

        # 로그창
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd; font-family: Consolas;")
        layout.addWidget(self.log_view)

        self.setLayout(layout)

    def log(self, message: str):
        self.log_view.append(message)
        # 스크롤 최하단 이동
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def start_conversion(self):
        url = self.input_url.text().strip()
        if not url:
            QMessageBox.warning(self, "입력 오류", "URL을 입력해주세요.")
            return

        if "build=" not in url and not url.startswith("v2d-"):
             QMessageBox.warning(self, "형식 오류", "올바른 SSToy 빌드 URL 형식이 아닙니다.")
             return

        self.btn_convert.setEnabled(False)
        self.input_url.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_view.clear()
        self.log("🚀 변환 시작...")

        # 워커 스레드 시작
        self.worker = ConverterWorker(url)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success: bool, message: str):
        self.btn_convert.setEnabled(True)
        self.input_url.setEnabled(True)
        
        if success:
            self.log(f"\n✅ {message}")
            QMessageBox.information(self, "성공", "빌드 파일이 성공적으로 생성되었습니다.")
            self.conversion_finished.emit() # 메인 윈도우에 알림
        else:
            self.log(f"\n❌ 오류 발생: {message}")
            QMessageBox.critical(self, "실패", f"변환 중 오류가 발생했습니다.\n{message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BuildMakerApp()
    window.show()
    sys.exit(app.exec_())