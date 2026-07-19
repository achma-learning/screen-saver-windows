"""
main.py
--------
Application entry point. Assumes dependencies are already installed --
run via bootstrap.py for automatic first-time dependency installation,
or run this directly once PySide6 / pywin32 are present.
"""

import sys


def main():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    # NOTE: earlier versions of this file called
    # ctypes.windll.shcore.SetProcessDpiAwareness() here, before
    # QApplication existed. That was a mistake: Qt 6's QApplication
    # already calls the modern SetProcessDpiAwarenessContext(
    # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2) internally during
    # construction. Windows only allows a process's DPI awareness to be
    # set ONCE -- our earlier manual call won that race, so Qt's own
    # (better) call then failed with "Access is denied" and the process
    # silently fell back to older, less capable V1 awareness (visible
    # as a qt.qpa.window warning at startup). Removing the manual call
    # lets Qt set the V2 context itself, which is what we want.

    # High-DPI pixmaps so icons/dialogs stay sharp on scaled displays.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # keep running in the tray with no visible windows
    app.setApplicationName("HtmlScreensaver")

    from PySide6.QtWidgets import QSystemTrayIcon, QMessageBox
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "HTML Screensaver",
                              "No system tray is available on this system.")
        sys.exit(1)

    from src.tray_app import TrayApp

    autostart_launch = "--autostart" in sys.argv
    tray_app = TrayApp(app, autostart_launch=autostart_launch)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
