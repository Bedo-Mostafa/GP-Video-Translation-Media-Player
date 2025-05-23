import os
import sys
from PySide6.QtWidgets import QApplication
from core.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Path relative to the project root (CWD)
    path_to_app_theme_css = os.path.join("ui//assets", "app-theme.css")

    # Load the light theme stylesheet
    with open(path_to_app_theme_css , 'r') as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
