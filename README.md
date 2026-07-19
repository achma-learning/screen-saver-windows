# HTML Screensaver for Windows 11

Runs any local HTML/CSS/JS/WebGL/Canvas/video file as a true full-screen,
multi-monitor Windows screensaver, with a tray-resident controller.

## Why this stack (read this before touching the code)

**PySide6 + QtWebEngine**, not WebView2, not Electron.

| Concern | PySide6 + QtWebEngine | WebView2 | Electron |
|---|---|---|---|
| Browser runtime | Bundled with the package (own Chromium) | Separate OS component, can be missing/outdated | Bundled, but duplicated per-app |
| Extra install step for the user | None | Must detect + install WebView2 Runtime | None, but heavy download |
| RAM/idle footprint | Low (single Python process) | Low | High (Node + Chromium always) |
| Multi-monitor + per-monitor DPI control | Direct via `QScreen` | Possible but more manual plumbing | Possible, heavier |
| Native tray icon / native dialogs | Built in (`QSystemTrayIcon`, `QFileDialog`, etc.) | Needs separate UI toolkit | Custom-built |

QtWebEngine satisfies every rendering requirement in the spec (WebGL,
Canvas, video, modern JS) while removing an entire dependency
(WebView2 Runtime) that could go missing or drift out of sync with the OS.

## Project layout

```
html_screensaver/
├── install.bat                 <- for users with NO Python installed at all
├── bootstrap.py                <- RUN THIS if Python is already installed (single entry point)
├── main.py                     <- app entry point (assumes deps installed)
├── build_exe.py                 <- optional: package into a standalone .exe
├── requirements.txt
├── demo_screensaver.html        <- sample file to test with
├── installer/
│   └── install_dependencies.py    <- detects & installs PySide6 / pywin32
└── src/
    ├── config_manager.py         <- JSON settings, stored in %APPDATA%
    ├── idle_detector.py          <- GetLastInputInfo-based idle time
    ├── autostart.py              <- HKCU Run-key management
    ├── fullscreen_detector.py    <- skips activation over games/movies/presentations
    ├── content_source.py         <- shared local-file-vs-URL resolution helper
    ├── screensaver_window.py     <- per-monitor fullscreen QWebEngineView + input-close logic
    ├── setup_wizard.py           <- first-run wizard + reopenable settings dialog
    └── tray_app.py               <- tray icon, menu, idle-poll loop, orchestration
```

## Recently added

- **10px mouse dead-zone** — dismiss threshold raised from a token 4px to a
  full 10px of cumulative movement, so wireless-mouse jitter (common:
  1-2px sensor noise while sitting still) can't falsely dismiss the
  screensaver the instant it appears.
- **Unified installer** — `bootstrap.py` is now a single guided flow:
  checks/installs Python packages → offers a **Desktop shortcut** (Y/N) →
  offers **Start with Windows** (Y/N) → offers building a **standalone
  .exe** (Y/N, installs PyInstaller on confirmation) → launches the app.
  `install.bat` covers the one case Python itself can't: installing
  Python via `winget` first, then chains into this same flow.
- **Fixed: DPI awareness "Access is denied" warning** — `main.py` used to
  call `SetProcessDpiAwareness()` manually before creating `QApplication`.
  Qt 6 already sets the (better) `DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2`
  internally during `QApplication` construction; Windows only allows a
  process's DPI awareness to be set once, so our earlier manual call was
  winning that race and silently downgrading Qt to older V1-style
  awareness. Removed the manual call entirely — Qt's own default is
  correct and now takes effect cleanly.
- **Fixed: "Object event filter cannot be in a different thread"** — the
  global input-detection filter was constructed with no parent, leaving
  its thread affinity unresolved before `installEventFilter` ran. It's
  now explicitly parented to the `QApplication` instance at construction
  (and `deleteLater()`'d on stop, so repeated screensaver activations
  don't accumulate filter objects over a long session).
- **Fullscreen-app detection** — `src/fullscreen_detector.py` compares the
  foreground window's rect to its monitor bounds; if a game, video
  player, or presentation is running exclusive-fullscreen, the idle poll
  skips activation entirely (toggle: tray menu → *Skip When a Fullscreen
  App Is Active*, on by default).
- **No console window** — `bootstrap.py` hands off to `main.py` via a
  **detached `pythonw.exe`** process rather than running the GUI in its
  own console-owning interpreter, so nothing black flashes up once setup
  finishes. `autostart.py` was already pointed at `pythonw.exe`.
- **Cursor hiding is explicit and reversible** — `Qt.BlankCursor` is
  (re-)applied on every `show_fullscreen_on_screen()` call and explicitly
  `unsetCursor()`'d in `closeEvent`, rather than relying on window
  teardown to implicitly restore it.
- **Dev mode** — tray menu → *Developer Mode*: disables the QtWebEngine
  HTTP cache and persistent cookies for the screensaver's profile, and
  watches the HTML file with `QFileSystemWatcher` so **saving your file
  auto-reloads every monitor's view** instantly. Meant to be turned on
  while iterating on the HTML/CSS/JS, off for normal use.
- **URLs as well as local files** — `content_source` in config accepts
  either an absolute local `.html` path or an `http(s)://` URL;
  `src/content_source.py` resolves whichever was given.

## First run

**No Python installed?** Double-click `install.bat` — it detects that,
offers to install Python via `winget` (Y/N), then continues into the same
guided installer below automatically.

**Python already installed?**

```powershell
python bootstrap.py
```

You'll be walked through, in order:

1. Dependency install (PySide6, pywin32) — confirmed per-package.
2. "Create a Desktop shortcut?" (Y/N)
3. "Start HTML Screensaver automatically when Windows starts?" (Y/N)
4. "Build a standalone .exe as well?" (Y/N) — installs PyInstaller on
   confirmation, then runs `build_exe.py`.
5. Launch, in the background, no console window.

Then, on the app's own first launch, the **Setup Wizard** appears: pick
your content (`.html` file or URL), set the inactivity timeout.

This will:

1. Check your Python version (3.9+).
2. Check for `PySide6` and `pywin32`. For anything missing, you'll see a
   prompt like:

   ```
   Qt6 + QtWebEngine (Chromium) -- renders the screensaver and UI
   PySide6 is required.
   Install now? (Y/N):
   ```

   Only confirmed installs proceed; nothing is installed silently.
3. Launch the app, which detects it's the first run and opens the
   **Setup Wizard**: pick your `.html` file, set the inactivity timeout,
   optionally enable "Start with Windows."
4. Drop into the system tray and start monitoring idle time immediately.

Try it with the included `demo_screensaver.html` (a starfield + clock) to
confirm everything works before pointing it at your own content.

## Tray menu

Right-click the tray icon for:

- **Enable / Disable Screensaver** — checkbox toggle, persists across restarts.
- **Start Screensaver Now** — manual trigger, useful for previewing.
- **Change HTML File...**
- **Change Inactivity Timeout...**
- **Open Settings...** — all options in one dialog.
- **Exit**

## Behavior details

- **Multi-monitor**: one independent full-screen window per `QScreen`,
  each loading the same HTML file — correct per-monitor DPI, no stretched
  or blurry mirroring.
- **Dismiss on input**: a Qt-level global event filter watches every
  screensaver window for mouse press, key press, wheel, touch, or a
  mouse move beyond a small dead-zone (avoids false triggers from
  hyper-sensitive trackpads/mice) and closes all windows immediately.
- **Hot-plug**: if a monitor is connected/disconnected while the
  screensaver is showing, the window set is rebuilt automatically to
  match.
- **Idle detection**: `GetLastInputInfo` polled once per second — a
  single sub-millisecond `ctypes` call, so CPU/RAM cost while idle is
  negligible.
- **Config**: stored as JSON at `%APPDATA%\HtmlScreensaver\config.json`.
  A simple log lives alongside it at `screensaver.log`.
- **Autostart**: writes/removes a value at
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` — no admin rights
  required, affects only the current user.

## Packaging as a standalone .exe (optional)

For distribution to users without Python installed:

```powershell
pip install pyinstaller
python build_exe.py
```

Produces `dist/HtmlScreensaver/HtmlScreensaver.exe`. Point users at that
folder instead of the Python scripts; `autostart.py` automatically
detects a frozen build (`sys.frozen`) and points the registry Run key at
the `.exe` rather than `pythonw.exe main.py`.

## Notes / known constraints

- Windows-only by design (`winreg`, `ctypes.windll`, `QSystemTrayIcon`
  behavior all assume Win32). Running on other platforms is only useful
  for editing the HTML content itself, not for testing the screensaver
  behavior.
- Password-protected lock-on-activate (the classic "require login to
  return to desktop" screensaver option) is not wired up here, since it
  requires invoking `LockWorkStation()` — mentioned in config as
  `lock_on_wake` for future extension, left off (`False`) by default.
