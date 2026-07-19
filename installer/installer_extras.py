"""
installer_extras.py
---------------------
Post-dependency-install steps for the unified installer in bootstrap.py:
  - creating a Desktop shortcut (.lnk)
  - triggering the optional PyInstaller standalone .exe build

Imported only *after* PySide6/pywin32 are confirmed installed, since it
uses `win32com.client` (from pywin32) to build the shortcut.
"""

from __future__ import annotations

import os
import subprocess
import sys


def create_desktop_shortcut(project_root: str) -> str | None:
    """
    Create 'HTML Screensaver.lnk' on the current user's Desktop, pointing
    at pythonw.exe main.py (no console window). Returns the shortcut
    path on success, or None if it couldn't be created.
    """
    try:
        import win32com.client
    except ImportError:
        print("pywin32 is not available -- cannot create a desktop shortcut.")
        return None

    desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
    if not os.path.isdir(desktop):
        print(f"Desktop folder not found at {desktop} -- skipping shortcut.")
        return None

    shortcut_path = os.path.join(desktop, "HTML Screensaver.lnk")

    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable

    main_py = os.path.join(project_root, "main.py")

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.TargetPath = pythonw
    shortcut.Arguments = f'"{main_py}"'
    shortcut.WorkingDirectory = project_root
    shortcut.IconLocation = pythonw
    shortcut.Description = "HTML Screensaver -- launch to the system tray"
    shortcut.Save()

    return shortcut_path


def build_standalone_exe(project_root: str) -> bool:
    """
    Runs build_exe.py (PyInstaller) to produce a standalone .exe that
    doesn't need Python installed to run. Installs PyInstaller first if
    it's missing (with confirmation, matching the rest of the installer's
    behavior). Returns True on success.
    """
    import importlib.util
    if importlib.util.find_spec("PyInstaller") is None:
        answer = input("PyInstaller is required to build a standalone .exe. Install now? (Y/N): ").strip().lower()
        if answer not in ("y", "yes"):
            print("Skipped building the standalone .exe.")
            return False
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"],
        )
        if result.returncode != 0:
            print("Failed to install PyInstaller.")
            return False

    print("Building standalone .exe (this can take a few minutes)...")
    build_script = os.path.join(project_root, "build_exe.py")
    result = subprocess.run([sys.executable, build_script], cwd=project_root)
    if result.returncode != 0:
        print("Build failed. See PyInstaller output above.")
        return False

    exe_path = os.path.join(project_root, "dist", "HtmlScreensaver", "HtmlScreensaver.exe")
    print(f"Standalone build complete: {exe_path}")
    return True
