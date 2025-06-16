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
