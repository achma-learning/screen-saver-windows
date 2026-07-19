"""
idle_detector.py
-----------------
Detects system-wide user idle time (mouse, keyboard, touch/pen -- anything
that feeds the Windows input stack) using the native GetLastInputInfo API.

This is the correct low-level approach on Windows: it does not require
hooking input events (expensive, fragile, can be flagged by AV software),
and it reflects *any* input across *all* processes and monitors, which a
Qt-level event filter would not (Qt only sees events destined for its own
windows).
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD),
    ]


def get_idle_seconds() -> float:
    """
    Return the number of seconds since the last user input event
    (mouse move/click, keyboard press, or touch/pen input) anywhere
    on the system.
    """
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        # If the call fails for some reason, report 0 idle so we never
        # accidentally trigger the screensaver on a broken read.
        return 0.0

    tick_count = ctypes.windll.kernel32.GetTickCount64()
    idle_ms = tick_count - lii.dwTime
    return idle_ms / 1000.0
