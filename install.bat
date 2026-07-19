@echo off
setlocal enabledelayedexpansion
title HTML Screensaver - Installer

echo ============================================================
echo  HTML Screensaver - Installer
echo ============================================================
echo.

rem --- Step 1: check for Python on PATH ---------------------------------
where python >nul 2>nul
if %errorlevel%==0 (
    echo [OK] Python was found on PATH.
    goto :run_bootstrap
)

echo Python was not found on this system.
echo.
echo Python is required.
set /p INSTALL_PY="Install now via winget? (Y/N): "
if /I not "%INSTALL_PY%"=="Y" (
    echo.
    echo Python is required to continue. Please install it manually from
    echo https://www.python.org/downloads/ and re-run this installer.
    pause
    exit /b 1
)

rem --- Step 2: check winget is available ---------------------------------
where winget >nul 2>nul
if not %errorlevel%==0 (
    echo.
    echo winget was not found on this system ^(it ships with Windows 11 by
    echo default -- if it's missing, your Windows install may need updating^).
    echo Please install Python manually from https://www.python.org/downloads/
    echo and re-run this installer.
    pause
    exit /b 1
)

echo.
echo Installing Python via winget. This may take a few minutes...
winget install --id Python.Python.3.12 --source winget --accept-package-agreements --accept-source-agreements
if not %errorlevel%==0 (
    echo.
    echo Automatic Python installation failed. Please install Python manually
    echo from https://www.python.org/downloads/ and re-run this installer.
    pause
    exit /b 1
)

echo.
echo Python installed. You may need to close and reopen this window for
echo PATH changes to take effect.
echo Please re-run install.bat now.
pause
exit /b 0

:run_bootstrap
echo.
echo Handing off to bootstrap.py for dependency checks and first-time setup...
echo.
python "%~dp0bootstrap.py"
pause
