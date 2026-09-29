# Universal Auto Typer

A beginner-friendly web app that takes any text — a sentence, a paragraph, or
100+ lines of code — and types it back out automatically, exactly as you
entered it. No trimming, no reformatting, no collapsed whitespace.

It supports plain text as well as code in Java, Python, C, C++, JavaScript,
HTML, CSS, SQL, JSON, Markdown, and anything else you paste in.

## Features

- Large paste-in text area that preserves spaces, tabs, blank lines, and indentation exactly, with a **Full screen** toggle for editing longer code comfortably (press Esc or the button again to exit)
- Adjustable typing speed (Normal / Fast / Very Fast / Custom delay in ms)
- Configurable countdown before typing starts, with the ability to cancel
- Repeat the text 1–100 times
- Live character and line counters
- Two typing modes:
  - **Browser mode** — types the text into an on-page output panel, character by character. Works anywhere this app is running, including online. Has its own **Clear output** button, independent from the input's **Clear** button — clearing one never touches the other.
  - **Local system mode** — types directly into whichever application currently has keyboard focus on your Windows computer, using a low-level Windows keyboard input API (no automation-library overhead, no clipboard tricks). Available two ways:
    - From inside this web app, when it's running locally (`run.bat`).
    - As a **completely standalone desktop app** (`UniversalAutoTyper.exe`, built with `build.bat`) that needs no project folder, terminal, Flask server, or browser at all — see [Local System Mode (standalone app)](#local-system-mode-standalone-app) below.
  - **Dismiss IDE autocomplete popups** (on by default in Local System Mode, both the web app and the standalone app) — sends Escape right before typing a space/punctuation character that follows a word, so an open autocomplete/suggestion popup in your editor gets closed instead of intercepting that keystroke. Turn it off if your target app doesn't have this kind of popup and you want one fewer keystroke per word.
- Global keyboard shortcuts: **Shift+Z** to start typing, **Shift+X** to stop immediately. Shown right on the Start/Stop buttons and as hover tooltips. In the standalone app these work no matter which window has focus; on the web page they work whenever the text box itself isn't focused.
- Clean, responsive, terminal-inspired UI that works on desktop, laptop, tablet, and mobile

## Technology

```
Python
Flask
HTML
CSS
JavaScript
ctypes + Win32 SendInput   (native Windows keyboard input, see winkeys.py)
Tkinter                    (standalone desktop app UI)
PyInstaller                (packages the standalone app into UniversalAutoTyper.exe)
keyboard                   (global Shift+Z / Shift+X hotkeys)
```

## Screenshots

_Add screenshots here after running the app:_

```
screenshots/homepage.png
screenshots/typing-in-progress.png
```

## Requirements

- Python 3.x
- Windows for local system-wide typing — Local System Mode (both the web app's version and the standalone app) uses the Win32 SendInput API directly, so it requires Windows. Browser Mode works on any OS.

## Running locally

The easiest way to run this app is with `run.bat`:

1. Download or clone this repository.
2. Double-click `run.bat`, or run it from Command Prompt:
   ```
   run.bat
   ```
3. `run.bat` will check for Python, create a virtual environment, install
   dependencies, and start the server automatically.
4. Open your browser to:
   ```
   http://127.0.0.1:5000
   ```

## Browser usage

Once the server is running (locally or deployed), open the app in your
browser, paste your text, choose a speed, countdown, and repeat count, and
click **Start typing** (or press **Shift+Z** while the text box isn't
focused). In Browser mode, the text is "typed" into the output panel right
there in the page — nothing leaves your browser tab.

The input area and the output panel each have their own **Clear** button.
Clicking **Clear** under the input empties only the input; clicking
**Clear output** under the output panel empties only the output. Clearing
one never affects the other.

## Local system mode (from the web app)

1. Select **Local system mode** in the app.
2. Click **Start typing** (or press **Shift+Z**).
3. During the countdown, click into the window/application you want the text
   typed into (a code editor, a chat box, a document, etc.).
4. When the countdown ends, the app types the text using your keyboard.
5. Press **Shift+X** at any time to stop immediately — this works globally,
   even if the browser doesn't have focus, as long as the local server is
   still running.

> Use responsibly. Only automate applications where you have permission to do so.

## Local System Mode (standalone app)

If you don't want to keep a project folder, terminal, or Flask server
running just to use Local System Mode, build it into a single double-click
desktop app instead:

1. Run `build.bat`. This installs the required dependencies (including
   [PyInstaller](https://pyinstaller.org)) into a throwaway build virtual
   environment and packages `local_app.py` into one file.
2. When it finishes, you'll have:
   ```
   dist\UniversalAutoTyper.exe
   ```
3. Copy that single `.exe` anywhere you like — your Desktop, a USB drive,
   another computer. It does **not** need the rest of the project folder,
   Python, or Flask to run.
4. Double-click `UniversalAutoTyper.exe`. A small desktop window opens
   directly — no browser, no terminal, no `run.bat`.
5. Paste or type your text into the window.
6. Click into your target application (Notepad, VS Code, IntelliJ IDEA,
   Chrome, or anything else) so it has keyboard focus.
7. Press **Shift+Z**. A short countdown begins, then the app types your
   text into whatever window currently has focus.
8. Press **Shift+X** at any time to stop immediately.

Both hotkeys are registered as **global** hotkeys (via the `keyboard`
package with key suppression), so they work no matter which application is
focused, and the letters "Z" and "X" are never actually typed into your
target application when used as the shortcut. On-screen Start/Stop buttons
are also available in the standalone window, each labeled with its hotkey
and showing a tooltip on hover.

> Use responsibly. Only automate applications where you have permission to do so.

### Why Local System Mode is fast now

Local System Mode used to go through a high-level automation library that
made one or more separate calls per character, with its own built-in
pauses. It's now built on `winkeys.py`, a thin wrapper around the Win32
**SendInput** API (via `ctypes`) — the same low-level mechanism Windows
itself uses to deliver input:

- Each standard character (letters, digits, and the punctuation/symbols
  code needs — `{}[]();:'"<>/\|` and friends) is sent as a **real
  virtual-key event**, resolved for your active keyboard layout via the
  Win32 `VkKeyScanW` lookup — the same one Windows itself uses. Each
  character gets its own distinct key, exactly like a physical keyboard,
  with Shift/Ctrl/Alt pressed and released around it only when that
  character actually needs one.
  - This is what fixed the *repeated*-character corruption
    (`(){` → `({{{{`): every character sent via the alternative
    `KEYEVENTF_UNICODE` approach shares virtual-key code 0, and Windows
    tracks "is this key still held down" (for its own auto-repeat) mainly
    by virtual-key code — so a fast run of different characters could
    occasionally confuse that tracking into repeating one. Giving each
    character its own real key removes that ambiguity.
  - A character your keyboard layout has no key for (most non-Latin
    scripts, emoji, symbols outside the layout) falls back to
    `KEYEVENTF_UNICODE`, so nothing is ever silently dropped.
- Enter and Tab are sent as real key presses (`VK_RETURN` / `VK_TAB`)
  rather than synthesized characters, so IDE behavior like auto-indent
  still triggers normally.
- Each key's down and up are sent as two separate `SendInput()` calls
  with a small settle gap between them (5ms), rather than being batched
  into one call with no gap at all. This matters for correctness, not
  just pacing: this input goes through Windows' own message-translation
  layer, and if the next character's key-down is injected before that
  translation has actually happened, the pending character can be
  overwritten before the target window reads it. That's what caused an
  earlier wave of corruption (`obj` → `bbj`, `new` → `nnnew`) — the total
  length stayed the same, but earlier characters were getting overwritten
  by later ones. The settle gap is a floor under every speed setting,
  including "Very fast" and a Custom delay of 0ms.
- **Dismiss IDE autocomplete popups** (on by default) sends a real
  Escape key right before typing a space/punctuation character that
  follows a word, closing any open autocomplete/suggestion popup so it
  can't intercept that keystroke — e.g. accepting a suggestion and
  silently replacing what you typed (`boolean` → `Boolean`) instead of
  letting the space through as plain text.

The speed presets were deliberately kept non-zero even at "Very fast" —
accuracy comes first. Current values: **Normal = 40ms, Fast = 30ms, Very
fast = 20ms** per character (on top of a 5ms settle gap on each side of
every key event). If you still see dropped or corrupted characters in a
particular application, use **Custom** to raise the per-character delay
for that app specifically — heavier apps (IDEs with live syntax checking,
autocomplete, etc.) need more headroom than a plain text editor does.

**Why this can never be a 100% guarantee:** SendInput has no way to ask
the target application "did you actually process that keystroke yet?" —
every delay here (the settle gap, and the per-character speed setting) is
an open-loop timing margin, not a confirmation. A busier application, a
slower/more loaded machine, or background processes competing for CPU can
all shift how much margin is actually needed. If corruption persists even
after raising Custom well above 40ms:
- Try typing into Notepad first. If that's clean but your IDE still
  corrupts text, the IDE itself (auto-import, live templates, or an
  on-keystroke analysis pass) is adding its own delay on top of what
  Windows needs, and needs an even larger Custom value.
- Close other software that hooks the keyboard (clipboard managers,
  other automation/macro tools, some security software) — a second hook
  competing for the same input stream can reintroduce exactly this kind
  of race.
- Check Windows Task Manager for CPU spikes while typing; a heavily
  loaded machine widens the gap needed for reliable delivery.

## Pushing to GitHub

```
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

## Docker

Build and run the container (Browser mode only — see Limitations below):

```
docker build -t universal-auto-typer .
docker run -p 5000:5000 universal-auto-typer
```

## Deployment

This app is ready to deploy to a platform such as [Render](https://render.com):

1. Push the repository to GitHub.
2. Create a new Web Service on Render pointing at the repo, using the
   included `Dockerfile`.
3. Render will provide a `PORT` environment variable automatically; the app
   already listens on `0.0.0.0` and reads `PORT` from the environment.

**Online deployment = Browser mode only.**
**Local `run.bat` = Browser mode + Local system mode (in the web app).**
**`build.bat` = standalone `UniversalAutoTyper.exe`, Local system mode only, no Flask needed.**

A deployed website can never type into a visitor's other desktop
applications — that would require access no browser or web server is
allowed to have. Local system mode is only possible because the Flask
server itself is running on your machine.

## Limitations

- Browser security prevents any website (deployed or local) from typing
  into applications outside the browser tab — that's what Local system mode
  is for, and it only works when you run the app yourself via `run.bat`.
- Local System Mode is **Windows-only** — it calls the Win32 SendInput API
  directly via `ctypes`, so it does not run on macOS or Linux. Browser Mode
  works everywhere.
- Very high speeds (an aggressively low Custom delay) can still outrun a
  particular target application's own input handling, even with the native
  backend's built-in settle gap — if you see dropped or reordered
  characters in a specific app, raise the Custom delay a little for that
  app.
- Standard characters are resolved against your **active Windows keyboard
  layout** (via `VkKeyScanW`), same as a real keyboard — this is what
  gives each character its own distinct key and avoids the repeat-glitch
  described above. A character your layout can't produce falls back to
  `KEYEVENTF_UNICODE`, so nothing is silently dropped, but if you switch
  keyboard layouts mid-session, typing follows whichever layout is active
  when each character is sent. The standalone app's own Shift+Z/Shift+X
  hotkey combination can also behave differently on unusual layouts.
- The target application you're typing into can affect reliability —
  some apps intercept or auto-format keystrokes (e.g. auto-indent in code
  editors, which is why Enter and Tab are sent as real key presses rather
  than synthesized characters).
- Local system typing requires running the app locally (via `run.bat`) or
  using the standalone `UniversalAutoTyper.exe` (via `build.bat`); it is not
  available in the Docker/deployed version.
- The global Shift+Z / Shift+X hotkeys rely on the `keyboard` package's
  low-level OS hook. On some systems this may require running as an
  administrator, and some target applications with their own low-level
  keyboard hooks (certain games, some remote-desktop clients) may not
  respect the suppression and could still see the raw keypress.
