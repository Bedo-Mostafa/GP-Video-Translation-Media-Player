import PyInstaller.__main__
import os
import shutil

os.environ["PYTHONOPTIMIZE"] = "2"

PyInstaller.__main__.run(["--noconfirm", "--noupx", "--clean", "main.py"])


def copy_folder(src, dst):
    try:
        dst = dst + "/" + src
        if not os.path.exists(src):
            print(f"Source folder does not exist: {src}")
            return

        if os.path.exists(dst):
            print(f"Destination folder already exists. Removing: {dst}")

        shutil.copytree(src, dst)
        print(f"Folder copied successfully from {src} to {dst}")
    except Exception as e:
        print(f"Error occurred: {e}")


destination_folder = "dist/main"

copy_folder("machine_models", destination_folder)
copy_folder("ui/assets", destination_folder)
