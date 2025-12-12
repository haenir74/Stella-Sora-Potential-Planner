import sys
import os
import ctypes
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

# [모듈 임포트]
from config import __version__, DEFAULT_BUILD_FILE, BUILDS_FOLDER, AppStatus
from src.worker import MatcherWorker
from src.overlay import OverlayWindow

ctypes.windll.user32.SetProcessDPIAware()

class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Potential Planner Controller v{__version__}")
        self.resize(320, 280) # UI가 커졌으므로 창 크기도 약간 조절
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        # 감시 상태 플래그
        self.is_monitoring = False 

        # UI 레이아웃
        layout = QVBoxLayout()
        layout.setSpacing(15) # 위젯 간 간격 넓힘

        # ------------------------------------------------
        # 1. 상태 표시 라벨 (크고 잘 보이게 변경)
        # ------------------------------------------------
        self.status_container = QWidget()
        status_layout = QVBoxLayout(self.status_container)
        
        self.lbl_title = QLabel("현재 상태 (Status)")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("color: #555; font-size: 10pt;")
        
        self.status_label = QLabel("리소스 로딩 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Malgun Gothic", 16, QFont.Bold))
        self.status_label.setStyleSheet("color: gray; margin-bottom: 5px;")
        
        status_layout.addWidget(self.lbl_title)
        status_layout.addWidget(self.status_label)
        layout.addWidget(self.status_container)

        # ------------------------------------------------
        # 2. 감시 제어 (재생/일시정지 버튼)
        # ------------------------------------------------
        self.btn_toggle = QPushButton("▶") # 기본값: 재생
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(False)
        self.btn_toggle.setMinimumHeight(60) # 최소 크기 보장
        self.btn_toggle.setMinimumWidth(150)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)

        # 초기 스타일
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #FFF0F0;
                color: #D32F2F;
                border: 1px solid #D32F2F;
                border-radius: 5px;
                font-size: 20pt; 
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFCDD2;
            }
        """)
        self.btn_toggle.clicked.connect(self.toggle_monitoring)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)               # 왼쪽 공백 (1)
        btn_layout.addWidget(self.btn_toggle, 3) # 버튼 (3) -> 전체의 60%
        btn_layout.addStretch(1)               # 오른쪽 공백 (1)

        layout.addLayout(btn_layout)

        # ------------------------------------------------
        # 3. 빌드 선택 그룹
        # ------------------------------------------------
        build_group = QGroupBox("빌드 선택")
        build_layout = QVBoxLayout()
        
        self.build_combo = QComboBox()
        self.refresh_build_list()
        self.build_combo.currentTextChanged.connect(self.on_build_changed)
        build_layout.addWidget(self.build_combo)
        
        btn_refresh = QPushButton("목록 새로고침")
        btn_refresh.clicked.connect(self.refresh_build_list)
        build_layout.addWidget(btn_refresh)
        
        build_group.setLayout(build_layout)
        layout.addWidget(build_group)

        # ------------------------------------------------
        # 4. 하단 옵션
        # ------------------------------------------------
        bottom_layout = QHBoxLayout()

        # (1) 오버레이 전체 켜기/끄기
        self.check_overlay = QCheckBox("오버레이 켜기")
        self.check_overlay.setChecked(True)
        self.check_overlay.stateChanged.connect(self.toggle_overlay)
        bottom_layout.addWidget(self.check_overlay)

        # (2) 디버그 정보 표시 (기본값: 꺼짐)
        self.check_debug = QCheckBox("디버그 정보")
        self.check_debug.setChecked(False) # 기본은 꺼둠
        self.check_debug.stateChanged.connect(self.toggle_debug)
        bottom_layout.addWidget(self.check_debug)
        
        # (3) 종료 버튼
        btn_quit = QPushButton("종료")
        btn_quit.setFixedWidth(80)
        btn_quit.clicked.connect(self.close_app)
        bottom_layout.addWidget(btn_quit)

        layout.addLayout(bottom_layout)
        self.setLayout(layout)

        # ------------------------------------------------
        # 작업자 실행
        # ------------------------------------------------
        self.overlay = OverlayWindow()

        # 초기 빌드 파일 경로 생성
        current_file = self.build_combo.currentText()
        if current_file and current_file != "빌드 파일 없음":
            initial_build_path = os.path.join(BUILDS_FOLDER, current_file)
        else:
            initial_build_path = ""

        self.worker = MatcherWorker(initial_build_path)

        self.worker.match_signal.connect(self.overlay.update_result)
        self.worker.reset_signal.connect(self.overlay.clear_all)
        self.worker.status_signal.connect(self.update_status_text)
        self.worker.initial_load_finished.connect(self.on_loading_complete)

        # 디버그 시그널 연결
        self.worker.debug_signal.connect(self.overlay.update_debug_info)

        self.overlay.show()
        self.worker.start()

    def on_loading_complete(self):
        self.toggle_monitoring()
        self.btn_toggle.setChecked(True)

    # 토글 로직 & UI
    def toggle_monitoring(self):
        self.is_monitoring = not self.is_monitoring
        self.worker.set_paused(not self.is_monitoring)

        if self.is_monitoring:
            # 감시 중 상태로 변경 (버튼은 '멈춤'을 유도)
            self.btn_toggle.setText("■") # 일시정지 아이콘
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #FFF0F0;
                    color: #D32F2F; 
                    border: 1px solid #D32F2F;
                    border-radius: 5px;
                    font-size: 20pt; 
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #FFCDD2; }
            """)
        else:
            # 일시정지 상태로 변경 (버튼은 '재생'을 유도)
            self.btn_toggle.setText("▶") # 재생 아이콘
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #E8F5E9;
                    color: #2E7D32;
                    border: 1px solid #2E7D32;
                    border-radius: 5px;
                    font-size: 24pt; 
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #C8E6C9; }
            """)

    def update_status_text(self, status: AppStatus, detail_text: str):
        """
        status: 현재 상태 (Enum)
        detail_text: Worker가 보낸 부가 설명 (필요 없다면 UI에서 정한 텍스트를 써도 됨)
        """

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
        self.build_combo.blockSignals(True)
        self.build_combo.clear()

        # builds 폴더가 없으면 생성
        if not os.path.exists(BUILDS_FOLDER):
            try:
                os.makedirs(BUILDS_FOLDER)
            except OSError:
                pass
        
        if os.path.exists(BUILDS_FOLDER):
            json_files = [f for f in os.listdir(BUILDS_FOLDER) if f.endswith('.json')]
        else:
            json_files = []

        if not json_files:
            self.build_combo.addItem("빌드 파일 없음")
            self.build_combo.setEnabled(False)
        else:
            self.build_combo.addItems(json_files)
            self.build_combo.setEnabled(True)
            if DEFAULT_BUILD_FILE in json_files:
                self.build_combo.setCurrentText(DEFAULT_BUILD_FILE)
        
        self.build_combo.blockSignals(False)
        
    def on_build_changed(self, text):
        if text and text.endswith(".json"):
            full_path = os.path.join(BUILDS_FOLDER, text)
            self.worker.update_build(full_path)

    def toggle_debug(self, state):
        self.overlay.set_debug_mode(self.check_debug.isChecked())
        
    def toggle_overlay(self, state):
        self.overlay.set_visibility(self.check_overlay.isChecked())

    def close_app(self):
        self.worker.stop()
        self.overlay.close()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec_())