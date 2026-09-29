"""
Universal Auto Typer - local desktop typing engine

Types raw text into whatever application currently has keyboard focus,
using the low-level Windows SendInput API (see winkeys.py) rather than a
high-level automation library. Runs in a background thread so the Flask
server / desktop GUI stays responsive, and supports a global emergency-stop
hotkey (Shift+X).

This module is used by two things:
  - The Flask app's web-based Local System Mode (app.py)
  - The standalone desktop app (local_app.py), which also registers a
    global Shift+Z "start" hotkey of its own on top of this engine.

It is only usable when running locally on Windows (via run.bat or the
standalone UniversalAutoTyper.exe). It has no effect on, and is not
reachable from, a deployed/online copy of the web app.
"""

import threading
import time
import logging

from winkeys import (
    NATIVE_INPUT_AVAILABLE,
    type_char as _native_type_char,
    press_escape,
    release_modifiers,
    _KEY_SETTLE_SECONDS,
)

log = logging.getLogger("universal-auto-typer.engine")

# --------------------------------------------------------------------------
# Optional dependency: keyboard (global Shift+X emergency stop, and
# Shift+Z start in the standalone app). Only available/functional on a
# real desktop session. Importing it can fail in headless/server
# environments (e.g. Docker on Render), so we degrade gracefully instead
# of crashing the whole app.
# --------------------------------------------------------------------------

try:
    import keyboard  # global hotkey listener for the Shift+X emergency stop
    KEYBOARD_AVAILABLE = True
except Exception as exc:  # pragma: no cover - depends on host environment
    keyboard = None
    KEYBOARD_AVAILABLE = False
    log.warning("keyboard module unavailable, Shift+X emergency stop disabled: %s", exc)


class TypingEngine:
    """
    Runs a typing job on a background thread and exposes simple
    start/stop/status controls that the Flask API can call.

    Status values:
        idle      - nothing has run yet, or the last job finished/was stopped
        counting  - countdown before typing begins
        typing    - actively sending keystrokes
        done      - finished all repeats successfully
        stopped   - stopped early (user Stop button or Shift+X)
        error     - an error occurred
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()
        self._hotkey_handle = None

        self._status = "idle"
        self._message = "Ready"
        self._countdown_remaining = 0
        self._chars_typed = 0
        self._chars_total = 0
        self._current_repeat = 0
        self._total_repeats = 1

        # Register the global Shift+X emergency-stop hotkey as soon as the
        # engine exists, rather than waiting for the first job to start,
        # so it works the instant the app (web or standalone) is open.
        self._register_emergency_stop()

    # ----------------------------------------------------------------
    # Public controls
    # ----------------------------------------------------------------

    def start(self, text, delay_ms, countdown, repeat, dismiss_popups=True):
        """Start a new typing job. Returns False if one is already running."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False

            self._stop_event.clear()
            self._status = "counting" if countdown > 0 else "typing"
            self._message = "Starting..."
            self._countdown_remaining = countdown
            self._chars_typed = 0
            repeat = max(1, repeat)                      # normalise once, used consistently below
            self._chars_total = len(text) * repeat
            self._current_repeat = 0
            self._total_repeats = repeat

            self._thread = threading.Thread(
                target=self._run,
                args=(text, delay_ms, countdown, repeat, dismiss_popups),
                daemon=True,
            )
            self._thread.start()
            return True

    def stop(self):
        """Signal the running job (if any) to stop as soon as possible."""
        with self._lock:
            if self._status in ("counting", "typing"):
                self._status = "stopped"
                self._message = "Stopped by user."
        self._stop_event.set()

    def get_status(self):
        with self._lock:
            return {
                "status": self._status,
                "message": self._message,
                "countdownRemaining": self._countdown_remaining,
                "charsTyped": self._chars_typed,
                "charsTotal": self._chars_total,
                "currentRepeat": self._current_repeat,
                "totalRepeats": self._total_repeats,
                "nativeInputAvailable": NATIVE_INPUT_AVAILABLE,
                "emergencyStopAvailable": KEYBOARD_AVAILABLE,
            }

    # ----------------------------------------------------------------
    # Internal
    # ----------------------------------------------------------------

    def _register_emergency_stop(self):
        if not KEYBOARD_AVAILABLE:
            return
        if self._hotkey_handle is not None:
            return
        try:
            # suppress=True swallows the physical Shift+X combo so it never
            # reaches the focused application as literal "X" text.
            self._hotkey_handle = keyboard.add_hotkey(
                "shift+x", self._on_emergency_stop, suppress=True
            )
        except Exception as exc:  # pragma: no cover - depends on OS permissions
            log.warning("Could not register Shift+X emergency stop: %s", exc)

    def _on_emergency_stop(self):
        log.info("Shift+X pressed: emergency stop triggered")
        with self._lock:
            if self._status in ("counting", "typing"):
                self._status = "stopped"
                self._message = "Emergency stopped (Shift+X)."
        self._stop_event.set()
        # Belt-and-suspenders: release any modifier keys in case the user's
        # own keypresses left one held down mid-shortcut. Typed characters
        # themselves never hold a modifier (see winkeys.type_char).
        release_modifiers()

    def _run(self, text, delay_ms, countdown, repeat, dismiss_popups=True):
        try:
            if not NATIVE_INPUT_AVAILABLE:
                with self._lock:
                    self._status = "error"
                    self._message = "Native keyboard input is not available on this machine (Windows required)."
                return

            # Countdown, giving the user time to click/focus the target app.
            for remaining in range(countdown, 0, -1):
                if self._stop_event.is_set():
                    return
                with self._lock:
                    self._status = "counting"
                    self._countdown_remaining = remaining
                    self._message = f"Starting in {remaining}..."
                time.sleep(1)

            with self._lock:
                self._status = "typing"
                self._message = "Typing..."
                self._countdown_remaining = 0

            delay_seconds = delay_ms / 1000.0
            # After press_escape() we must wait long enough for the IDE's event
            # thread to actually dismiss the popup before the next character
            # arrives. IDE event threads (IntelliJ EDT, VS Code renderer) can
            # take 15-20 ms to close a popup. Using max(delay_seconds, 2×SETTLE)
            # ensures this gap is at least as long as the user's own
            # inter-character delay (which they've confirmed is safe), and never
            # shorter than 16 ms even at the fastest custom speed. This is what
            # caused 'boolean' → 'Boolean': Escape fired but the popup was still
            # open when '(' arrived, so the IDE accepted its 'Boolean' suggestion.
            escape_settle_seconds = max(delay_seconds, _KEY_SETTLE_SECONDS * 2)

            for rep in range(1, repeat + 1):
                if self._stop_event.is_set():
                    return
                with self._lock:
                    self._current_repeat = rep

                prev_was_identifier = False
                for char in text:
                    if self._stop_event.is_set():
                        return

                    is_identifier = char.isalnum() or char == "_"
                    if dismiss_popups and prev_was_identifier and not is_identifier:
                        # Finishing a word (identifier/keyword) and about to
                        # type something else - e.g. "Scanner" -> space,
                        # "new" -> "(", "arr" -> ";". This is exactly where
                        # an IDE's autocomplete popup is most likely to be
                        # open and intercept the next keystroke instead of
                        # letting it through as plain text. Escape closes
                        # any such popup first; it's a no-op if none is
                        # open, so this is safe even when it wasn't needed.
                        press_escape()
                        time.sleep(escape_settle_seconds)

                    self._type_char(char)
                    prev_was_identifier = is_identifier
                    with self._lock:
                        self._chars_typed += 1
                    if delay_seconds > 0:
                        time.sleep(delay_seconds)

            with self._lock:
                self._status = "done"
                self._message = "Finished."

        except Exception as exc:  # pragma: no cover - defensive
            log.exception("Typing job failed")
            with self._lock:
                self._status = "error"
                self._message = f"Typing error: {exc}"

    @staticmethod
    def _type_char(char):
        """
        Send a single character to the focused application via the
        native Windows SendInput backend (see winkeys.py). Characters
        that can't be sent are skipped rather than mistyped, since
        silently substituting a wrong character would corrupt code and
        text - winkeys already logs a warning when this happens.
        """
        _native_type_char(char)
