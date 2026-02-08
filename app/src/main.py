import sys
import os
import ctypes
import logging
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QCheckBox, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

try:
    from config import __version__, DEFAULT_BUILD_FILE, PRESETS_DIR, AppStatus, check_essential_directories
    from src.worker import MatcherWorker
    from src.overlay import OverlayWindow
except ImportError as e:
    ctypes.windll.user32.MessageBoxW(0, f"필수 모듈 로드 실패: {e}", "Error", 0x10)
    sys.exit(1)

# 선택적 모듈 (빌드 생성기)
BuildMaker = None
try:
    from sstoy_loader.build_maker import BuildMaker
except ImportError:
    try:
        from src.sstoy_loader.build_maker import BuildMaker
    except ImportError as e:
        logging.error(f"빌드 생성기 로드 실패: {e}")

# 로거 설정
from src.logger import setup_logging
logger = logging.getLogger("MainGUI")

# 고해상도 모니터(DPI) 대응
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Potential Planner Controller v{__version__}")
        self.resize(320, 280)
        self.setWindowFlags(Qt.WindowStaysOnTopHint) # 컨트롤 패널도 항상 위에 표시

        # 상태 변수
        self.is_monitoring: bool = False 
        self.build_maker_window: Optional[QWidget] = None

        # 1. 초기 검증 (필수 폴더 존재 확인)
        try:
            check_essential_directories()
        except FileNotFoundError as e:
            QMessageBox.critical(self, "초기화 오류", str(e))
            sys.exit(1)

        # 2. UI 구성
        self._init_ui()

        # 3. 워커 및 오버레이 초기화
        self._init_worker_and_overlay()

        logger.info("GUI 초기화 완료")

    def _init_ui(self):
        """UI 레이아웃 구성"""
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # --- [A] 상태 표시 ---
        self.status_container = QWidget()
        status_layout = QVBoxLayout(self.status_container)
        
        self.lbl_title = QLabel("현재 상태 (Status)")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("color: #555; font-size: 10pt;")
        
        self.status_label = QLabel("준비 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Malgun Gothic", 16, QFont.Bold))
        self.status_label.setStyleSheet("color: gray; margin-bottom: 5px;")
        
        status_layout.addWidget(self.lbl_title)
        status_layout.addWidget(self.status_label)
        layout.addWidget(self.status_container)

        # --- [B] 재생/일시정지 버튼 ---
        self.btn_toggle = QPushButton("▶")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(False)
        self.btn_toggle.setMinimumHeight(60)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_monitoring)
        self._update_toggle_btn_style(False) # 초기 스타일 설정

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_toggle, 3)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        # --- [C] 빌드 선택 영역 ---
        build_group = QGroupBox("빌드 선택 (Preset)")
        build_vbox = QVBoxLayout()

        self.build_combo = QComboBox()
        self.refresh_build_list()
        self.build_combo.currentTextChanged.connect(self.on_build_changed)
        build_vbox.addWidget(self.build_combo)
        
        # 버튼 그룹 (새로고침 / 생성기)
        btn_hbox = QHBoxLayout()
        
        btn_refresh = QPushButton("새로고침")
        btn_refresh.clicked.connect(self.refresh_build_list)
        btn_hbox.addWidget(btn_refresh)

        btn_maker = QPushButton("URL로 생성 (+)")
        btn_maker.setStyleSheet("color: #1976D2; font-weight: bold;")
        btn_maker.clicked.connect(self.open_build_maker)
        btn_hbox.addWidget(btn_maker)
        
        build_vbox.addLayout(btn_hbox)
        build_group.setLayout(build_vbox)
        layout.addWidget(build_group)

        # --- [D] 하단 옵션 ---
        bottom_layout = QHBoxLayout()
        self.check_overlay = QCheckBox("오버레이 켜기")
        self.check_overlay.setChecked(True)
        self.check_overlay.stateChanged.connect(self.toggle_overlay)
        bottom_layout.addWidget(self.check_overlay)

        self.check_debug = QCheckBox("디버그 정보")
        self.check_debug.setChecked(False)
        self.check_debug.stateChanged.connect(self.toggle_debug)
        bottom_layout.addWidget(self.check_debug)
        
        btn_quit = QPushButton("종료")
        btn_quit.setFixedWidth(80)
        btn_quit.clicked.connect(self.close_app)
        bottom_layout.addWidget(btn_quit)

        layout.addLayout(bottom_layout)
        self.setLayout(layout)

    def _init_worker_and_overlay(self):
        """워커 스레드와 오버레이 윈도우 초기화"""
        self.overlay = OverlayWindow()
        
        # 초기 빌드 파일 경로 설정
        current_file = self.build_combo.currentText()
        if current_file and current_file != "빌드 파일 없음":
            initial_build_path = PRESETS_DIR / current_file
        else:
            initial_build_path = ""

        # Worker 생성 (문자열 경로 대신 Path 객체를 문자열로 변환하여 전달)
        self.worker = MatcherWorker(str(initial_build_path))

        # 시그널 연결
        self.worker.match_signal.connect(self.overlay.update_result)
        self.worker.reset_signal.connect(self.overlay.clear_all)
        self.worker.status_signal.connect(self.update_status_text)
        self.worker.initial_load_finished.connect(self.on_loading_complete)
        self.worker.debug_signal.connect(self.overlay.update_debug_info)
        self.worker.geometry_signal.connect(self.overlay.update_geometry)

        # 시작
        self.overlay.show()
        self.worker.start()

    # ------------------------------------------------------
    # 이벤트 핸들러
    # ------------------------------------------------------
    def on_loading_complete(self):
        """리소스 로딩이 끝나면 자동으로 감시 시작"""
        self.toggle_monitoring()
        self.btn_toggle.setChecked(True)

    def toggle_monitoring(self):
        """시작/정지 토글"""
        self.is_monitoring = not self.is_monitoring
        self.worker.set_paused(not self.is_monitoring)
        self._update_toggle_btn_style(self.is_monitoring)

    def _update_toggle_btn_style(self, is_running: bool):
        if is_running:
            self.btn_toggle.setText("■")
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #FFF0F0; color: #D32F2F; border: 1px solid #D32F2F;
                    border-radius: 5px; font-size: 20pt; font-weight: bold;
                }
                QPushButton:hover { background-color: #FFCDD2; }
            """)
        else:
            self.btn_toggle.setText("▶")
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #E8F5E9; color: #2E7D32; border: 1px solid #2E7D32;
                    border-radius: 5px; font-size: 24pt; font-weight: bold;
                }
                QPushButton:hover { background-color: #C8E6C9; }
            """)

    def update_status_text(self, status: AppStatus, detail_text: str):
        """상태 라벨 업데이트"""
        if status == AppStatus.LOADING:
            display_text = "로딩 중..."
            style = "color: gray; font-size: 14pt;"
        elif status == AppStatus.IDLE:
            display_text = "게임 검색 중..."
            style = "color: #555; font-size: 14pt;"
        elif status == AppStatus.RUNNING:
            display_text = "실행 중 (Running)"
            style = "color: #4CAF50; font-size: 16pt; font-weight: bold;"
        elif status == AppStatus.PAUSED:
            display_text = "일시정지 (Paused)"
            style = "color: #FF9800; font-size: 16pt; font-weight: bold;"
        elif status == AppStatus.ERROR:
            display_text = f"오류: {detail_text}"
            style = "color: red; font-size: 14pt; font-weight: bold;"
        else:
            display_text = detail_text
            style = "color: black;"

        self.status_label.setText(display_text)
        self.status_label.setStyleSheet(style)

    def refresh_build_list(self):
        """PRESETS_DIR 폴더를 스캔하여 콤보박스 갱신"""
        self.build_combo.blockSignals(True)
        self.build_combo.clear()

        # 폴더가 없으면 생성 시도
        if not PRESETS_DIR.exists():
            try:
                PRESETS_DIR.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error(f"프리셋 폴더 생성 실패: {e}")

        # JSON 파일 목록 스캔
        json_files = []
        if PRESETS_DIR.exists():
            json_files = [f.name for f in PRESETS_DIR.iterdir() if f.is_file() and f.suffix.lower() == '.json']

        if not json_files:
            self.build_combo.addItem("빌드 파일 없음")
            self.build_combo.setEnabled(False)
        else:
            self.build_combo.addItems(sorted(json_files))
            self.build_combo.setEnabled(True)
            if DEFAULT_BUILD_FILE in json_files:
                self.build_combo.setCurrentText(DEFAULT_BUILD_FILE)
        
        self.build_combo.blockSignals(False)
        
    def on_build_changed(self, text):
        """콤보박스 변경 시 Worker에 알림"""
        if text and text.endswith(".json"):
            full_path = PRESETS_DIR / text
            self.worker.update_build(str(full_path))

    def open_build_maker(self):
        """빌드 생성기 창 열기"""
        if BuildMaker is None:
            QMessageBox.critical(self, "오류", "빌드 생성기 모듈을 찾을 수 없습니다.\n(src/sstoy_loader 폴더 확인 필요)")
            return

        if self.build_maker_window is not None and self.build_maker_window.isVisible():
            self.build_maker_window.raise_()
            self.build_maker_window.activateWindow()
            return

        self.build_maker_window = BuildMaker()
        # 생성 완료 시 리스트 새로고침 연결
        self.build_maker_window.conversion_finished.connect(self.refresh_build_list)
        self.build_maker_window.show()

    def toggle_debug(self, state):
        self.overlay.set_debug_mode(self.check_debug.isChecked())
        
    def toggle_overlay(self, state):
        self.overlay.set_visibility(self.check_overlay.isChecked())

    def close_app(self):
        """앱 종료 처리"""
        logger.info("종료 요청 수신")
        if self.worker.isRunning():
            self.worker.stop()
        
        self.overlay.close()
        self.close()

if __name__ == "__main__":
    setup_logging()
    app = QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec_())