"""
setup_wizard.py
-----------------
Two dialogs:
  - SetupWizard: shown once, on first run, to collect the HTML file,
    timeout, and autostart preference.
  - SettingsDialog: the same fields, reachable any time from the tray
    menu ("Open Settings"), pre-filled with current values.

Both use native Qt widgets (QFileDialog, QSpinBox, QCheckBox) which
render with the current Windows 11 theme, including dark mode, since
Qt on Windows follows the OS theme automatically from Qt 6.5+.
"""

from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QDialog, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QCheckBox, QFileDialog, QFormLayout,
    QDialogButtonBox,
)

from .config_manager import ConfigManager
from . import autostart


class _ContentSourcePicker(QHBoxLayout):
    """Accepts either a local .html file path (via Browse...) or a
    typed/pasted http(s):// URL directly in the text field."""

    def __init__(self, initial_value: str = ""):
        super().__init__()
        self.line_edit = QLineEdit(initial_value)
        self.line_edit.setPlaceholderText("Local .html file path, or https://...")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse)
        self.addWidget(self.line_edit)
        self.addWidget(self.browse_btn)

    def _browse(self):
        start_dir = os.path.dirname(self.line_edit.text()) or os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            None, "Select HTML Screensaver File", start_dir, "HTML Files (*.html *.htm)"
        )
        if path:
            self.line_edit.setText(path)

    def path(self) -> str:
        return self.line_edit.text().strip()


class SetupWizard(QWizard):
    """Shown exactly once, right after first install."""

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HTML Screensaver -- First-Time Setup")
        self.setWizardStyle(QWizard.ModernStyle)
        self._config_manager = config_manager

        self._page = QWizardPage()
        self._page.setTitle("Configure your screensaver")
        self._page.setSubTitle("Choose the HTML file or URL to display and when it should start.")

        layout = QFormLayout()

        self._picker = _ContentSourcePicker(config_manager.config.content_source)
        layout.addRow("Content:", self._picker)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1, 240)
        self._timeout_spin.setValue(config_manager.config.timeout_minutes or 10)
        self._timeout_spin.setSuffix(" minutes")
        layout.addRow("Start after:", self._timeout_spin)

        self._autostart_check = QCheckBox("Start HTML Screensaver automatically when Windows starts")
        self._autostart_check.setChecked(config_manager.config.autostart)
        layout.addRow("", self._autostart_check)

        self._page.setLayout(layout)
        self.addPage(self._page)

        self.finished.connect(self._on_finished)

    def _on_finished(self, result: int):
        if result != QDialog.Accepted:
            return
        content_source = self._picker.path()
        self._config_manager.update(
            content_source=content_source,
            timeout_minutes=self._timeout_spin.value(),
            autostart=self._autostart_check.isChecked(),
            enabled=True,
            first_run_complete=True,
        )
        autostart.set_enabled(self._autostart_check.isChecked())


class SettingsDialog(QDialog):
    """Reopenable settings dialog, available from the tray menu at any time."""

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HTML Screensaver -- Settings")
        self._config_manager = config_manager

        layout = QFormLayout(self)

        cfg = config_manager.config
        self._picker = _ContentSourcePicker(cfg.content_source)
        layout.addRow("Content:", self._picker)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1, 240)
        self._timeout_spin.setValue(cfg.timeout_minutes)
        self._timeout_spin.setSuffix(" minutes")
        layout.addRow("Start after:", self._timeout_spin)

        self._autostart_check = QCheckBox("Start with Windows")
        self._autostart_check.setChecked(cfg.autostart)
        layout.addRow("", self._autostart_check)

        self._enabled_check = QCheckBox("Screensaver enabled")
        self._enabled_check.setChecked(cfg.enabled)
        layout.addRow("", self._enabled_check)

        self._skip_fullscreen_check = QCheckBox("Skip when a fullscreen app (game/movie) is active")
        self._skip_fullscreen_check.setChecked(cfg.skip_if_fullscreen_app)
        layout.addRow("", self._skip_fullscreen_check)

        self._dev_mode_check = QCheckBox("Developer mode (disable cache, auto-reload on file change)")
        self._dev_mode_check.setChecked(cfg.dev_mode)
        layout.addRow("", self._dev_mode_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.accepted.connect(self._save)

    def _save(self):
        self._config_manager.update(
            content_source=self._picker.path(),
            timeout_minutes=self._timeout_spin.value(),
            autostart=self._autostart_check.isChecked(),
            enabled=self._enabled_check.isChecked(),
            skip_if_fullscreen_app=self._skip_fullscreen_check.isChecked(),
            dev_mode=self._dev_mode_check.isChecked(),
        )
        autostart.set_enabled(self._autostart_check.isChecked())
