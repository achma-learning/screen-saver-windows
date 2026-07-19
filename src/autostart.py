"""
autostart.py
-------------
Manages the "Start with Windows" preference by writing/removing a value
under HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.

HKCU (not HKLM) is used deliberately: it requires no admin elevation and
only affects the current user, which is the correct scope for a
per-user screensaver preference.
"""

from __future__ import annotations

import sys
import winreg

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "HtmlScreensaver"


def _launch_command() -> str:
    """
    Build the command line Windows should run at logon.
    If frozen (e.g. via PyInstaller), sys.executable is the .exe itself.
    Otherwise, invoke the current interpreter against main.py with
    --autostart so the app knows it was launched silently at boot.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --autostart'
    import os
    main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    return f'"{pythonw}" "{main_py}" --autostart'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except FileNotFoundError:
        return False


def set_enabled(enabled: bool) -> None:
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _launch_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
