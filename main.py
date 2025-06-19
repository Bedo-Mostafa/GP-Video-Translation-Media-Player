import sys
import site
import os
import subprocess


def get_external_site_packages():
    """Get site-packages path from external Python installation"""

    # If not frozen (development), use standard method
    if not getattr(sys, "frozen", False):
        site_packages = site.getsitepackages()
        user_site = site.getusersitepackages()
        if user_site and os.path.exists(user_site):
            site_packages.append(user_site)

        for path in site_packages:
            if os.path.exists(path) and "_MEI" not in path and "Roaming" not in path:
                return path

    # For frozen executables, try to find system Python
    print("Frozen executable detected, searching for system Python...")

    # Method 1: Try subprocess to get site-packages from system Python
    try:
        result = subprocess.run(
            'python -c "import site; print(site.getsitepackages()[1])"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            if os.path.exists(path):
                print(f"Found via subprocess: {path}")
                return path
    except:
        pass

    # Method 2: Check common installation paths
    username = os.getenv("USERNAME")
    common_paths = [
        f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages",
        f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\site-packages",
        f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Python\\Python310\\Lib\\site-packages",
        "C:\\Python311\\Lib\\site-packages",
        "C:\\Python312\\Lib\\site-packages",
        "C:\\Python310\\Lib\\site-packages",
    ]

    for path in common_paths:
        if os.path.exists(path):
            print(f"Found via common paths: {path}")
            return path

    # Method 3: Your original fallback logic (but fixed)
    try:
        # Don't use the bundle directory, use a system directory
        if getattr(sys, "frozen", False):
            # Try to find Python installation
            possible_bases = [
                "C:\\Python311",
                "C:\\Python312",
                "C:\\Python310",
                f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Python\\Python311",
                f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Python\\Python312",
            ]

            for base in possible_bases:
                if os.path.exists(base):
                    site_packages = os.path.join(base, "Lib", "site-packages")
                    if os.path.exists(site_packages):
                        print(f"Found via base search: {site_packages}")
                        return site_packages
    except:
        pass

    print("Could not find external site-packages")
    return None


# Your original code structure, but with better detection
external_site_packages_base = get_external_site_packages()

if external_site_packages_base:
    # Your code was adding another "Lib/site-packages" which was wrong
    # The function already returns the full site-packages path
    external_site_packages = external_site_packages_base

    print(f"Using external site-packages: {external_site_packages}")

    if external_site_packages not in sys.path:
        sys.path.insert(0, external_site_packages)
        print("Added to sys.path successfully")

        # List contents to verify
        if os.path.exists(external_site_packages):
            print("Installed libraries in site-packages:")
            items = os.listdir(external_site_packages)

            # Show important packages first
            important = ["torch", "numpy", "cv2", "PIL", "torchvision"]
            found_important = []

            for item in items:
                for imp in important:
                    if imp.lower() in item.lower():
                        full_path = os.path.join(external_site_packages, item)
                        if os.path.isdir(full_path):
                            found_important.append(f"  ✓ {item} (directory)")
                        else:
                            found_important.append(f"  ✓ {item} (file)")
                        break

            # Print important packages first
            for item in found_important:
                print(item)

            # Then show a few other items
            other_items = [
                item
                for item in items
                if not any(imp.lower() in item.lower() for imp in important)
            ]
            print(f"  ... and {len(other_items)} other packages")

    else:
        print("Path already in sys.path")
else:
    print("❌ Failed to find external site-packages")
    print("Available sys.path entries:")
    for i, path in enumerate(sys.path[:5]):
        print(f"  {i}: {path}")


# --- End of Workaround ---

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
