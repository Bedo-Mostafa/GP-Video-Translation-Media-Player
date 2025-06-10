import PyInstaller.__main__
import os
import shutil

os.environ["PYTHONOPTIMIZE"] = "2"

# Run PyInstaller to create a single executable
PyInstaller.__main__.run(
    [
        "--noconfirm",
        "--clean",
        "-F",
        # "--windowed",
        "--exclude-module=torch",
        "--exclude-module=tensorflow",
        "--exclude-module=faster_whisper",
        # "--exclude-module=transformers.trainer",  # Exclude training utilities
        "--exclude-module=numpy",
        "--exclude-module=scipy",
        "--exclude-module=opencv_python",
        "--exclude-module=opencv_python_headless",
        # transformers exclusions
        "--exclude-module=transformers.pipelines",
        "--exclude-module=transformers.generation",
        "--exclude-module=transformers.optimization",
        "--exclude-module=transformers.models",  # Exclude unused models
        "--exclude-module=transformers.trainer",
        "--exclude-module=transformers.trainer_utils",
        "--exclude-module=transformers.trainer_callback",
        "--exclude-module=transformers.benchmark",
        "--exclude-module=transformers.commands",
        "--exclude-module=transformers.convert_graph_to_onnx",
        "--exclude-module=transformers.integrations",
        "--exclude-module=transformers.tokenization_bert",
        "--exclude-module=transformers.tokenization_gpt2",
        "--exclude-module=transformers.tokenization_t5",
        # New transformers exclusions
        "--exclude-module=transformers.tokenization_albert",
        "--exclude-module=transformers.tokenization_bart",
        "--exclude-module=transformers.tokenization_distilbert",
        "--exclude-module=transformers.tokenization_electra",
        "--exclude-module=transformers.tokenization_roberta",
        "--exclude-module=transformers.tokenization_xlnet",
        "--exclude-module=transformers.tokenization_t5_fast",
        "--exclude-module=transformers.feature_extraction_utils",
        "--exclude-module=transformers.image_processing_utils",
        "--exclude-module=transformers.audio_utils",
        "--exclude-module=transformers.data",
        "--exclude-module=transformers.data.datasets",
        "--exclude-module=transformers.data.metrics",
        "--exclude-module=transformers.data.processors",
        "--exclude-module=transformers.testing_utils",
        "--exclude-module=transformers.debug_utils",
        "--exclude-module=transformers.modeling_tf_utils",
        "--exclude-module=transformers.modeling_flax_utils",
        "--exclude-module=transformers.onnx",
        "--exclude-module=transformers.sagemaker",
        "--exclude-module=transformers.tools",
        "--exclude-module=transformers.utils.hub",
        "main.py",
    ]
)


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
