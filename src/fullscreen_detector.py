"""
fullscreen_detector.py
------------------------
Detects whether the current foreground window is an exclusive-fullscreen
application (game, video player, presentation software) so the idle
monitor can skip activation -- standard, expected behavior for any
Windows screensaver; nothing should pop over a game or a movie.

Algorithm: compare the foreground window's rect against the full bounds
of the monitor it's on. A borderless window whose rect exactly covers
its monitor (no title bar, no taskbar visible) is treated as fullscreen.
The desktop/shell windows themselves are explicitly excluded so an empty
desktop doesn't get misread as "fullscreen app."
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

EXCLUDED_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd"}
MONITOR_DEFAULTTONEAREST = 2


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long), ("top", ctypes.c_long),
        ("right", ctypes.c_long), ("bottom", ctypes.c_long),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
        ("rcWork", RECT), ("dwFlags", wintypes.DWORD),
    ]


def _window_class_name(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def is_fullscreen_app_active() -> bool:
    """True if the foreground window covers its entire monitor (an
    exclusive/borderless-fullscreen app is in front)."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False

    if _window_class_name(hwnd) in EXCLUDED_CLASSES:
        return False

    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False

    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return False
    mon = info.rcMonitor

    return (
        rect.left <= mon.left and rect.top <= mon.top
        and rect.right >= mon.right and rect.bottom >= mon.bottom
    )
