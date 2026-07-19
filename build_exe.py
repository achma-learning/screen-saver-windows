"""
build_exe.py
-------------
Optional: packages the application into a standalone .exe with PyInstaller
so end users don't need Python installed at all. Run this yourself as the
developer/distributor; end users just get the resulting dist/ folder.

Usage:
    pip install pyinstaller
    python build_exe.py

Produces:
    dist/HtmlScreensaver/HtmlScreensaver.exe   (windowed, no console, tray-only)
"""

import subprocess
import sys

PYINSTALLER_ARGS = [
    sys.executable, "-m", "PyInstaller",
    "--name=HtmlScreensaver",
    "--windowed",              # no console window -- this is a tray app
    "--onedir",                 # onedir starts faster than onefile; fine for a tray app
    "--noconfirm",
    "--collect-all=PySide6",    # ensures QtWebEngine's Chromium resources are bundled
    "main.py",
]

if __name__ == "__main__":
    print("Building standalone executable with PyInstaller...")
    result = subprocess.run(PYINSTALLER_ARGS)
    if result.returncode == 0:
        print("\nBuild complete: dist/HtmlScreensaver/HtmlScreensaver.exe")
        print("To enable 'Start with Windows', autostart.py will point the")
        print("registry Run key at this .exe automatically once frozen.")
    else:
        print("\nBuild failed. See PyInstaller output above.")
        sys.exit(result.returncode)
