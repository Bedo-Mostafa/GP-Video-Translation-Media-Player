from os import path
from sys import exit, argv
from PySide6.QtWidgets import QApplication
from core.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(argv)
    # Path relative to the project root (CWD)
    path_to_app_theme_css = path.join("ui//assets", "app-theme.css")

    # Load the light theme stylesheet
    with open(path_to_app_theme_css, "r") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    exit(app.exec())
