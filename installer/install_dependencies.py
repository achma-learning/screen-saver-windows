"""
install_dependencies.py
-------------------------
Detects and installs everything the application needs, prompting the
user for confirmation before each install as required:

    "PySide6 (Qt6 + QtWebEngine/Chromium) is required. Install now? (Y/N)"

Because the chosen stack is PySide6 + QtWebEngine (which bundles its own
Chromium runtime), no separate Microsoft Edge WebView2 Runtime install is
needed -- this removes an entire class of "system component out of sync"
failures that a WebView2-based design would carry. `pywin32` is used for
a couple of Windows-registry/COM conveniences.

This module is intentionally standalone (only stdlib imports) so it can
run *before* any third-party package is confirmed to exist.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys


REQUIRED_PACKAGES = [
    # (import name, pip package spec, human description)
    ("PySide6", "PySide6>=6.6,<7", "Qt6 + QtWebEngine (Chromium) -- renders the screensaver and UI"),
    ("win32api", "pywin32>=306", "Windows registry / system integration helpers"),
]


def _is_installed(import_name: str) -> bool:
    return importlib.util.find_spec(import_name) is not None


def _prompt_yes_no(message: str) -> bool:
    while True:
        answer = input(f"{message} (Y/N): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer Y or N.")


def _pip_install(package_spec: str) -> bool:
    print(f"Installing {package_spec} ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", package_spec],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"ERROR: failed to install {package_spec} (exit code {result.returncode}).")
        return False
    print(f"{package_spec} installed successfully.")
    return True


def check_and_install_all(assume_yes: bool = False) -> bool:
    """
    Walk through every required package, prompting before each install
    (unless assume_yes is set, e.g. for silent/automated CI runs).
    Returns True if all requirements are satisfied by the end, False if
    the user declined a required install or an install failed.
    """
    print("=" * 60)
    print("HTML Screensaver -- Dependency Check")
    print("=" * 60)

    all_ok = True
    for import_name, pip_spec, description in REQUIRED_PACKAGES:
        if _is_installed(import_name):
            print(f"[OK] {import_name} is already installed.")
            continue

        print(f"\n{description}")
        print(f"{pip_spec.split('>=')[0].split('<')[0]} is required.")
        proceed = assume_yes or _prompt_yes_no("Install now?")
        if not proceed:
            print(f"Skipped installing {import_name}. The application cannot run without it.")
            all_ok = False
            continue

        if not _pip_install(pip_spec):
            all_ok = False

    print("=" * 60)
    if all_ok:
        print("All dependencies satisfied.")
    else:
        print("One or more required dependencies are missing. Exiting.")
    print("=" * 60)
    return all_ok


if __name__ == "__main__":
    ok = check_and_install_all(assume_yes="--yes" in sys.argv)
    sys.exit(0 if ok else 1)
