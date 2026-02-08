import sys
import os
import re
import logging
import importlib
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTextEdit, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

# 로거 설정
logger = logging.getLogger("BuildMaker")

# =========================================================
# [Import] 표준 상대 경로 방식
# =========================================================
try:
    from config import PRESETS_DIR
    from . import decoder
    from . import formatter
except ImportError as e:
    current_path = Path(__file__).resolve()
    app_root = current_path.parent.parent.parent
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))
    from config import PRESETS_DIR
    import decoder
    import formatter

# =========================================================
# 클래스 구현
# =========================================================

class ConverterWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        # [모듈 새로고침]
        try:
            importlib.reload(decoder)
            importlib.reload(formatter)
        except Exception as e:
            logger.warning(f"Reload failed: {e}")

        self.log_signal.emit(f"작업 시작: {self.url[:60]}...")
        
        # [수정] 파일명이 아닌 '폴더 경로'만 준비
        output_dir = str(PRESETS_DIR)
        
        try:
            self.log_signal.emit("Formatter 실행 중...")
            
            # [수정] formatter에게 폴더 경로 전달 -> formatter가 이름 결정
            success, result_msg = formatter.save_build_to_json(self.url, output_dir)
            
            if success:
                saved_path = result_msg  # 성공 시 경로가 반환됨
                self.progress_signal.emit(100)
                self.log_signal.emit(f"성공! 저장됨:\n{saved_path}")
                
                # 파일명만 추출해서 메시지박스에 표시
                file_name = os.path.basename(saved_path)
                self.finished_signal.emit(True, f"저장 완료: {file_name}")
            else:
                self.log_signal.emit(f"실패: {result_msg}")
                self.finished_signal.emit(False, result_msg)
                
        except Exception as e:
            logger.exception(f"Error: {e}")
            self.log_signal.emit(f"오류: {str(e)}")
            self.finished_signal.emit(False, str(e))

class BuildMaker(QWidget):
    conversion_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.worker = None

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("SSToy 빌드 가져오기")
        title.setFont(QFont("Malgun Gothic", 14, QFont.Bold))
        layout.addWidget(title)

        desc = QLabel("SSToy URL을 입력하면 앱용 빌드 파일로 변환합니다.")
        layout.addWidget(desc)

        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("https://jforplay.github.io/sstoy/app.html#build=...")
        layout.addWidget(self.input_url)

        self.btn_convert = QPushButton("변환 및 저장")
        self.btn_convert.setFixedHeight(40)
        self.btn_convert.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; border-radius: 5px;")
        self.btn_convert.clicked.connect(self.start_conversion)
        layout.addWidget(self.btn_convert)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #f8f9fa; border: 1px solid #ddd;")
        layout.addWidget(self.log_view)

        self.setLayout(layout)

    def log(self, message: str):
        self.log_view.append(message)
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def start_conversion(self):
        url = self.input_url.text().strip()
        if not url:
            QMessageBox.warning(self, "오류", "URL을 입력해주세요.")
            return

        if "build=" not in url and not re.search(r"v\d+[dr]-", url):
            QMessageBox.warning(self, "오류", "올바른 SSToy URL 형식이 아닙니다.")
            return

        self.btn_convert.setEnabled(False)
        self.input_url.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_view.clear()
        
        self.worker = ConverterWorker(url)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success: bool, message: str):
        self.btn_convert.setEnabled(True)
        self.input_url.setEnabled(True)
        if success:
            QMessageBox.information(self, "성공", message) # 메시지에 파일명 포함됨
            self.conversion_finished.emit()
        else:
            QMessageBox.critical(self, "실패", message)

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = BuildMaker()
    window.show()
    sys.exit(app.exec_())