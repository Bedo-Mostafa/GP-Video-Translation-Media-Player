import sys
import os

# The path to the external site-packages directory
# IMPORTANT: You might need to hardcode this path if the dynamic find fails.
# e.g., external_site_packages = 'C:\\Users\\YourUser\\AppData\\Local\\Programs\\Python\\Python39\\Lib\\site-packages'
# external_site_packages = (
#     "C:\\Users\\Bedo\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages"
# )

# if external_site_packages and external_site_packages not in sys.path:
#     print(f"Attempting to add external site-packages: {external_site_packages}")
#     sys.path.insert(0, external_site_packages)

import sys
import site
import os
import sysconfig


def get_external_site_packages():
    # Check if running as a PyInstaller bundle
    if getattr(sys, "frozen", False):
        # Get the path to the Python interpreter used to build the executable
        python_executable = sys.executable
        if sys.platform == "win32":
            # Derive the base Python installation directory
            python_base = os.path.dirname(os.path.dirname(python_executable))
            # Get the site-packages path using sysconfig
            site_packages = sysconfig.get_path("purelib", vars={"base": python_base})
            if os.path.exists(site_packages) and "Roaming" not in site_packages:
                return site_packages
    else:
        # Not frozen, prioritize local site-packages
        username = os.path.expanduser("~").split("\\")[-1]
        preferred_path = os.path.join(
            "C:\\Users",
            username,
            "AppData",
            "Local",
            "Programs",
            "Python",
            "Python311",
            "Lib",
            "site-packages",
        )
        if os.path.exists(preferred_path):
            return preferred_path

    # Fallback to check other site-packages
    site_packages = site.getsitepackages()
    user_site = site.getusersitepackages()
    all_paths = site_packages + [user_site] if user_site else site_packages

    for path in all_paths:
        if os.path.exists(path) and "Roaming" not in path:
            return path

    return None


external_site_packages = get_external_site_packages()

if external_site_packages and external_site_packages not in sys.path:
    print(f"Attempting to add external site-packages: {external_site_packages}")
    sys.path.insert(0, external_site_packages)

# --- End of Workaround ---


# Now, your regular imports can proceed
try:
    import torch

    print("Successfully imported torch version:", torch.__version__)
except ImportError as e:
    print("FATAL: Could not import PyTorch.")
    print(
        "Please ensure PyTorch is installed in the Python environment this app is being run with."
    )
    input("Press Enter to exit.")
    sys.exit(1)

try:
    import transformers

    print("Successfully imported transformers version:", transformers.__version__)
except ImportError as e:
    print("FATAL: Could not import transformers.")
    print(
        "Please ensure transformers is installed in the Python environment this app is being run with."
    )
    input("Press Enter to exit.")
    sys.exit(1)

# (rest of your main.py)


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
