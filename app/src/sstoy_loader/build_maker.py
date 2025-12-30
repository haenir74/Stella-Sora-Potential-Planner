import sys
import os
import json
import re
import requests
from . import decoder

try:
    from config import CHARACTER_DB_URL, POTENTIAL_DB_URL, CHAR_NAME_DB_URL, BUILDS_FOLDER
except ImportError:
    # 혹시 모를 경로 에러 대비 (단독 실행 등)
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from config import CHARACTER_DB_URL, POTENTIAL_DB_URL, CHAR_NAME_DB_URL, BUILDS_FOLDER

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

# === 설정 ===
REPO_BASE_URL = "https://raw.githubusercontent.com/JforPlay/sstoy/refs/heads/main/public/data"
CHARACTER_DB_URL = f"{REPO_BASE_URL}/Character.json"
POTENTIAL_DB_URL = f"{REPO_BASE_URL}/Potential.json"
CHAR_NAME_DB_URL = f"{REPO_BASE_URL}/EN/Character.json"

# 저장 경로 설정
SAVE_DIR = BUILDS_FOLDER

class ConverterWorker(QThread):
    log_signal = pyqtSignal(str)       # 로그 메시지 전송
    progress_signal = pyqtSignal(int)  # 진행률 (0~100)
    finished_signal = pyqtSignal(bool, str) # 성공 여부, 결과 메시지

    def __init__(self, url):
        super().__init__()
        self.url = url

    def fetch_db(self, url, name):
        self.log_signal.emit(f"📥 {name} 데이터 다운로드 중...")
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"{name} 다운로드 실패: {e}")

    def build_id_mapping(self, db_json):
        if not db_json: return []
        all_ids = [int(k) for k in db_json.keys()]
        return sorted(list(set(all_ids)))

    def get_real_id(self, mapped_idx, id_map):
        if 0 < mapped_idx <= len(id_map):
            return id_map[mapped_idx - 1]
        return None

    def get_program_char_key(self, real_id, name_db):
        if not name_db: return f"unknown_{real_id}"
        key = f"Character.{real_id}.1"
        english_name = name_db.get(key, f"Unknown_{real_id}")
        formatted_key = english_name.lower().replace(" ", "_")
        formatted_key = re.sub(r'[^a-z0-9_]', '', formatted_key)
        return formatted_key

    def sanitize_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def run(self):
        try:
            self.progress_signal.emit(10)

            # 1. DB 다운로드
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
            
            # 4. 저장 폴더 확인
            if not os.path.exists(SAVE_DIR):
                os.makedirs(SAVE_DIR)
                self.log_signal.emit(f"📂 폴더 생성됨: {SAVE_DIR}")

            output_path = os.path.join(SAVE_DIR, safe_filename)
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
                
                real_char_id = self.get_real_id(data['mapped_char_idx'], char_map)
                char_key = self.get_program_char_key(real_char_id, name_db)
                
                self.log_signal.emit(f"  - [{pos.upper()}] ID:{real_char_id} -> Key: \"{char_key}\"")
                
                potentials_dict = {}
                for mapped_pot_idx in data['mapped_potentials']:
                    real_pot_id = self.get_real_id(mapped_pot_idx, pot_map)
                    
                    # [중요] 마크가 없으면 기본값 2 (사용자 요청)
                    priority = data['marks'].get(mapped_pot_idx, 2)
                    potentials_dict[str(real_pot_id)] = priority
                    
                result_json["characters"][char_key] = potentials_dict

            # 6. 파일 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result_json, f, indent=2, ensure_ascii=False)
            
            self.progress_signal.emit(100)
            self.finished_signal.emit(True, f"저장 완료!\n경로: {output_path}")

        except Exception as e:
            self.finished_signal.emit(False, str(e))

class BuildMakerApp(QWidget):
    conversion_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SSToy Build Converter")
        self.resize(500, 450)
        self.initUI()
        self.worker = None

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
        desc = QLabel("공유받은 URL을 입력하면 프로그램용 빌드 파일로 변환하여\n[app/resources/presets] 폴더에 저장합니다.")
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

    def log(self, message):
        self.log_view.append(message)
        # 스크롤 최하단 이동
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def start_conversion(self):
        url = self.input_url.text().strip()
        if not url:
            QMessageBox.warning(self, "입력 오류", "URL을 입력해주세요.")
            return

        if "build=" not in url:
            QMessageBox.warning(self, "형식 오류", "올바른 SSToy 빌드 URL이 아닙니다.")
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

    def on_finished(self, success, message):
        self.btn_convert.setEnabled(True)
        self.input_url.setEnabled(True)
        
        if success:
            self.log(f"\n✅ {message}")
            QMessageBox.information(self, "성공", "빌드 파일이 성공적으로 생성되었습니다.")
            self.conversion_finished.emit()
        else:
            self.log(f"\n❌ 오류 발생: {message}")
            QMessageBox.critical(self, "실패", f"변환 중 오류가 발생했습니다.\n{message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 고해상도 모니터 대응
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

    window = BuildMakerApp()
    window.show()
    sys.exit(app.exec_())