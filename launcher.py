import sys
import ctypes

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from monitor.main_window import MainWindow

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
    "SigCorp.IA.Monitor"
)

app = QApplication(sys.argv)

icon = QIcon("assets/icon.ico")

app.setWindowIcon(icon)

window = MainWindow()
window.setWindowIcon(icon)

window.show()

sys.exit(app.exec())