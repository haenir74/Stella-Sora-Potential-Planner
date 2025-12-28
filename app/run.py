import sys
import os
from PyQt5.QtWidgets import QApplication

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.main import ControlPanel

if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec_())