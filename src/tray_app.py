"""
tray_app.py
------------
The application's main controller:
  - Lives in the system tray with a right-click menu.
  - Runs a low-overhead QTimer poll (once per second) checking idle time
    via idle_detector.get_idle_seconds() against the configured timeout.
  - Launches ScreensaverController when the threshold is crossed.
  - Exposes Enable/Disable/Start Now/Change HTML/Change Timeout/Settings/Exit.

Performance note: polling once per second with a single ctypes call is
effectively free (sub-millisecond, no allocations) -- there is no
meaningful CPU/RAM cost versus event-driven idle detection, and it is far
simpler and more robust than trying to hook global input events.
"""

from __future__ import annotations

import sys
import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QBrush
from PySide6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox, QFileDialog,
    QInputDialog, QWidget,
)

from .config_manager import ConfigManager, log
from .idle_detector import get_idle_seconds
from .screensaver_window import ScreensaverController
from .setup_wizard import SetupWizard, SettingsDialog
from .content_source import is_valid_source
from . import autostart
from . import fullscreen_detector

POLL_INTERVAL_MS = 1000


def _build_tray_icon() -> QIcon:
    """Generate a simple monitor-glyph icon at runtime so the app needs no
    external .ico asset to ship or go missing."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(QColor("#2D7DFF")))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(4, 8, 56, 38, 6, 6)
    painter.setBrush(QBrush(QColor("#0B1B33")))
    painter.drawRect(8, 12, 48, 30)
    painter.setBrush(QBrush(QColor("#2D7DFF")))
    painter.drawRect(26, 46, 12, 8)
    painter.drawRoundedRect(18, 54, 28, 5, 2, 2)
    painter.end()
    return QIcon(pixmap)


class TrayApp:
    def __init__(self, app: QApplication, autostart_launch: bool = False):
        self.app = app
        self.config_manager = ConfigManager()
        self._screensaver: ScreensaverController | None = None
        self._is_showing = False

        # Hidden parent widget so dialogs have a proper Qt parent/owner.
        self._root = QWidget()
        self._root.setWindowFlags(Qt.Tool)
        self._root.hide()

        self.tray_icon = QSystemTrayIcon(_build_tray_icon(), self.app)
        self.tray_icon.setToolTip("HTML Screensaver")
        self._build_menu()
        self.tray_icon.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self._check_idle)
        self.timer.start(POLL_INTERVAL_MS)

        if not self.config_manager.config.first_run_complete:
            self._run_first_time_setup()
        elif not autostart_launch:
            # Only pop a notification on a manual launch, not a silent
            # boot-time autostart, to avoid nagging the user at every login.
            self.tray_icon.showMessage(
                "HTML Screensaver",
                "Running in the system tray.",
                QSystemTrayIcon.Information,
                3000,
            )

    # ---------- Menu ----------

    def _build_menu(self):
        menu = QMenu()

        self.action_enable = QAction("Enable Screensaver", checkable=True)
        self.action_enable.setChecked(self.config_manager.config.enabled)
        self.action_enable.triggered.connect(self._toggle_enabled)
        menu.addAction(self.action_enable)

        menu.addSeparator()

        act_start_now = QAction("Start Screensaver Now")
        act_start_now.triggered.connect(self.start_screensaver)
        menu.addAction(act_start_now)

        menu.addSeparator()

        act_change_html = QAction("Change HTML File or URL...")
        act_change_html.triggered.connect(self._change_content_source)
        menu.addAction(act_change_html)

        act_change_timeout = QAction("Change Inactivity Timeout...")
        act_change_timeout.triggered.connect(self._change_timeout)
        menu.addAction(act_change_timeout)

        act_settings = QAction("Open Settings...")
        act_settings.triggered.connect(self._open_settings)
        menu.addAction(act_settings)

        menu.addSeparator()

        self.action_dev_mode = QAction("Developer Mode (disable cache + auto-reload)", checkable=True)
        self.action_dev_mode.setChecked(self.config_manager.config.dev_mode)
        self.action_dev_mode.triggered.connect(self._toggle_dev_mode)
        menu.addAction(self.action_dev_mode)

        self.action_skip_fullscreen = QAction("Skip When a Fullscreen App Is Active", checkable=True)
        self.action_skip_fullscreen.setChecked(self.config_manager.config.skip_if_fullscreen_app)
        self.action_skip_fullscreen.triggered.connect(self._toggle_skip_fullscreen)
        menu.addAction(self.action_skip_fullscreen)

        menu.addSeparator()

        act_exit = QAction("Exit")
        act_exit.triggered.connect(self._exit)
        menu.addAction(act_exit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._open_settings()

    # ---------- Actions ----------

    def _toggle_enabled(self, checked: bool):
        self.config_manager.update(enabled=checked)

    def _change_content_source(self):
        # Offer both paths: type/paste a URL directly, or browse for a
        # local file -- QInputDialog's line edit accepts either, and a
        # "Browse..." affordance lives in the full Settings dialog for
        # anyone who'd rather pick a file with a native dialog.
        current = self.config_manager.config.content_source
        text, ok = QInputDialog.getText(
            None, "Content Source",
            "Enter a local .html file path or a http(s):// URL\n"
            "(leave blank and click Browse in Settings to pick a file instead):",
            text=current,
        )
        if ok and text.strip():
            self.config_manager.update(content_source=text.strip())

    def _toggle_dev_mode(self, checked: bool):
        self.config_manager.update(dev_mode=checked)

    def _toggle_skip_fullscreen(self, checked: bool):
        self.config_manager.update(skip_if_fullscreen_app=checked)

    def _change_timeout(self):
        current = self.config_manager.config.timeout_minutes
        value, ok = QInputDialog.getInt(
            None, "Inactivity Timeout", "Start screensaver after (minutes):",
            current, 1, 240, 1
        )
        if ok:
            self.config_manager.update(timeout_minutes=value)

    def _open_settings(self):
        dlg = SettingsDialog(self.config_manager, self._root)
        dlg.exec()
        cfg = self.config_manager.config
        self.action_enable.setChecked(cfg.enabled)
        self.action_dev_mode.setChecked(cfg.dev_mode)
        self.action_skip_fullscreen.setChecked(cfg.skip_if_fullscreen_app)

    def _run_first_time_setup(self):
        wizard = SetupWizard(self.config_manager, self._root)
        wizard.exec()

    def _exit(self):
        self.timer.stop()
        self.tray_icon.hide()
        self.app.quit()

    # ---------- Idle monitoring ----------

    def _check_idle(self):
        cfg = self.config_manager.config
        if not cfg.enabled or self._is_showing:
            return
        if not is_valid_source(cfg.content_source):
            return

        if cfg.skip_if_fullscreen_app and fullscreen_detector.is_fullscreen_app_active():
            # A game, movie, or presentation is currently running
            # exclusive-fullscreen -- never interrupt it. Idle time keeps
            # accumulating; the check simply re-runs on the next poll.
            return

        idle_seconds = get_idle_seconds()
        timeout_seconds = cfg.timeout_minutes * 60
        if idle_seconds >= timeout_seconds:
            self.start_screensaver()

    def start_screensaver(self):
        cfg = self.config_manager.config
        if self._is_showing:
            return
        if not is_valid_source(cfg.content_source):
            self.tray_icon.showMessage(
                "HTML Screensaver",
                "No valid HTML file or URL is configured. Right-click the tray icon to select one.",
                QSystemTrayIcon.Warning,
                4000,
            )
            return

        log(f"Starting screensaver with {cfg.content_source} (dev_mode={cfg.dev_mode})")
        self._is_showing = True
        self._screensaver = ScreensaverController(cfg.content_source, self.app, dev_mode=cfg.dev_mode)
        self._screensaver.closed.connect(self._on_screensaver_closed)
        self._screensaver.start()

    def _on_screensaver_closed(self):
        log("Screensaver closed by user input")
        self._is_showing = False
        self._screensaver = None
