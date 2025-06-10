import PyInstaller.__main__
import os
import shutil

os.environ["PYTHONOPTIMIZE"] = "2"

PyInstaller.__main__.run(["--noconfirm", "--noupx", "--clean", "main.py"])


def copy_folder(src, dst):
    try:
        dst = os.path.join(dst, src)
        if not os.path.exists(src):
            print(f"Source folder does not exist: {src}")
            return

        if os.path.exists(dst):
            print(f"Destination folder already exists. Removing: {dst}")
            shutil.rmtree(dst)

        shutil.copytree(src, dst)
        print(f"Folder copied successfully from {src} to {dst}")
    except Exception as e:
        print(f"Error occurred: {e}")


# Copy necessary folders to dist/main
destination_folder = "dist/main"
copy_folder("machine_models", destination_folder)
copy_folder("ui/assets", destination_folder)


# import PyInstaller.__main__
# import os
# import shutil

# os.environ["PYTHONOPTIMIZE"] = "2"

# # --- Define all modules to exclude ---
# # These modules will be used from the external site-packages
# # instead of being bundled into the .exe
# excluded_modules = [
#     "torch",
#     "tensorflow",
#     "transformers",
#     "faster_whisper",
#     "numpy",
#     "opencv_python",
#     "opencv_python_headless",
#     "scipy",  # Often a large dependency of the above
# ]

# # Build the command-line arguments for PyInstaller
# pyinstaller_args = [
#     "--noconfirm",
#     "--clean",
#     "-F",  # Creates a single-file executable
#     # "--windowed", # Uncomment this if you have a GUI and no console
#     "main.py",
# ]

# # Add all the exclude flags
# for module in excluded_modules:
#     pyinstaller_args.insert(-1, f"--exclude-module={module}")

# print("Running PyInstaller with the following arguments:")
# print(pyinstaller_args)

# # Run PyInstaller with the constructed arguments
# PyInstaller.__main__.run(pyinstaller_args)


# def copy_folder(src, dst):
#     try:
#         # Create the full destination path
#         full_dst_path = os.path.join(dst, os.path.basename(src))

#         if not os.path.exists(src):
#             print(f"Source folder does not exist: {src}")
#             return

#         if os.path.exists(full_dst_path):
#             print(f"Destination folder already exists. Removing: {full_dst_path}")
#             shutil.rmtree(full_dst_path)

#         shutil.copytree(src, full_dst_path)
#         print(f"Folder copied successfully from {src} to {full_dst_path}")
#     except Exception as e:
#         print(f"Error occurred while copying '{src}': {e}")


# # Ensure the base destination directory exists before copying
# dist_folder = "dist/main"
# if not os.path.exists(dist_folder):
#     # For a single-file build (-F), the output is just dist/main.exe
#     # We need to create a directory to copy assets into
#     dist_folder = "dist"  # The output directory for a single file is 'dist'

# # Copy necessary local folders to the distribution directory
# copy_folder("machine_models", dist_folder)
# copy_folder("ui/assets", dist_folder)
