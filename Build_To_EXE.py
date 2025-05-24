import PyInstaller.__main__
import os

os.environ['PYTHONOPTIMIZE'] = '2'

PyInstaller.__main__.run([
    '--noconfirm',
    '--add-data', 'ui/assets/app-theme.css;.',
    '--add-data', 'ui/assets/animationLoader.html;.',
    '--clean',
    'main.py'
])