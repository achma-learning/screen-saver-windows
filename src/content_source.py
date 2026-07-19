"""
content_source.py
-------------------
Small shared helper so both local .html files and remote URLs can be
used as the screensaver content, without every call site re-implementing
the http(s):// check.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl


def is_url(content_source: str) -> bool:
    return content_source.strip().lower().startswith(("http://", "https://"))


def resolve_url(content_source: str) -> QUrl:
    content_source = content_source.strip()
    if is_url(content_source):
        return QUrl(content_source)
    return QUrl.fromLocalFile(content_source)


def is_valid_source(content_source: str) -> bool:
    """True if the source is either a reachable-looking URL or an
    existing local file. (URL reachability itself is checked at load
    time by QtWebEngine, not here -- this only rules out empty/garbage
    config values before we try to show anything.)"""
    import os
    content_source = (content_source or "").strip()
    if not content_source:
        return False
    if is_url(content_source):
        return True
    return os.path.isfile(content_source)
