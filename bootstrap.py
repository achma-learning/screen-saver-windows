"""
bootstrap.py
=============
THIS is the single file a user runs to get started:

    python bootstrap.py

It will:
  1. Verify the Python version is adequate.
  2. Check for and install missing dependencies (with Y/N confirmation
     before each install), by delegating to installer/install_dependencies.py.
  3. Hand off to main.py, which shows the first-run setup wizard the very
     first time, then starts the tray application and idle monitor.

Nothing here requires admin rights: pip installs to the user's own
Python environment, and the app only ever writes to HKCU and %APPDATA%.
"""

from __future__ import annotations

import os
import subprocess
import sys

MIN_PYTHON = (3, 9)


def _check_python_version():
    if sys.version_info < MIN_PYTHON:
        print(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required. "
            f"You are running {sys.version_info.major}.{sys.version_info.minor}."
        )
        print("Please install a current Python from https://www.python.org/downloads/")
        print("and re-run this script.")
        sys.exit(1)


def _check_platform():
    if sys.platform != "win32":
        print("This application is designed for Windows 11 and will not")
        print("function correctly (system tray, registry autostart, and")
        print("multi-monitor fullscreen all rely on Windows-only APIs).")
        answer = input("Continue anyway for development purposes? (Y/N): ").strip().lower()
        if answer not in ("y", "yes"):
            sys.exit(1)


def _prompt_yes_no(message: str) -> bool:
    while True:
        answer = input(f"{message} (Y/N): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer Y or N.")


def _launch_gui_detached(project_root: str):
    """
    Hand off to main.py via pythonw.exe (the windowless interpreter) in
    a fully detached process, so the console window this bootstrap ran
    in can close immediately and no black console window lingers behind
    the tray app for the rest of the session.
    """
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        # Fall back to the interpreter we're already running under (e.g.
        # non-Windows dev environments, or unusual Python installs that
        # ship without pythonw.exe).
        pythonw = sys.executable

    main_py = os.path.join(project_root, "main.py")
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(
        [pythonw, main_py],
        cwd=project_root,
        creationflags=creationflags,
        close_fds=True,
    )


def main():
    _check_python_version()
    _check_platform()

    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)

    print("=" * 60)
    print("HTML Screensaver -- Unified Installer")
    print("=" * 60)

    # ---- 1. Python packages (PySide6, pywin32) -----------------------
    from installer.install_dependencies import check_and_install_all
    if not check_and_install_all():
        print("\nSetup did not complete because required dependencies were not installed.")
        print("Run this installer again when you're ready.")
        sys.exit(1)

    # ---- 2. Desktop shortcut (optional) -------------------------------
    print()
    if sys.platform == "win32" and _prompt_yes_no("Create a Desktop shortcut?"):
        from installer.installer_extras import create_desktop_shortcut
        shortcut_path = create_desktop_shortcut(project_root)
        if shortcut_path:
            print(f"Shortcut created: {shortcut_path}")

    # ---- 3. Start with Windows (optional) ------------------------------
    print()
    if sys.platform == "win32" and _prompt_yes_no("Start HTML Screensaver automatically when Windows starts?"):
        from src import autostart
        from src.config_manager import ConfigManager
        autostart.set_enabled(True)
        ConfigManager().update(autostart=True)
        print("Autostart enabled.")

    # ---- 4. Standalone .exe build (optional) ---------------------------
    print()
    if _prompt_yes_no("Build a standalone .exe as well (no Python needed to run it)?"):
        from installer.installer_extras import build_standalone_exe
        build_standalone_exe(project_root)

    # ---- 5. Launch -------------------------------------------------------
    print()
    print("Launching HTML Screensaver in the background (no console window)...")
    _launch_gui_detached(project_root)
    print("Done. Look for the icon in your system tray.")


if __name__ == "__main__":
    main()
