"""
Universal Auto Typer - standalone Local System Mode application

A self-contained Tkinter desktop app. It does NOT use Flask and does NOT
open a browser — it IS the Local System typing tool. Build it into a
single .exe with build.bat (see PyInstaller command there) and double-
click the result to use it directly.

Workflow:
    1. Double-click UniversalAutoTyper.exe
    2. Paste/enter text into this window
    3. Click into the target application (Notepad, VS Code, IntelliJ, etc.)
    4. Press Shift+Z to start typing (after the countdown)
    5. Press Shift+X at any time to stop immediately

Shift+Z and Shift+X are registered as GLOBAL hotkeys (via the `keyboard`
package) with suppress=True, so they work no matter which window has
focus, and the letters "Z" / "X" are never actually typed into the
target application when used as the hotkey combo.
"""

import queue
import tkinter as tk
from tkinter import ttk, messagebox

from auto_typer import TypingEngine, NATIVE_INPUT_AVAILABLE, KEYBOARD_AVAILABLE

try:
    import keyboard
except Exception:
    keyboard = None


APP_TITLE = "Universal Auto Typer — Local System Mode"

# Delay-per-character presets (milliseconds). Chosen to prioritize
# accuracy: with the native SendInput backend there is no automation-
# library overhead left to trim, so the remaining delay exists purely to
# give the target application (an IDE's editor component, in particular)
# time to process each keystroke without dropping or reordering input.
# "Very fast" is deliberately non-zero for the same reason - a true 0ms
# gap can outrun what some editors can keep up with. Custom lets you push
# lower (or higher) if your target application can handle it.
SPEED_PRESETS = {
    "Normal (40 ms)": 40,
    "Fast (30 ms)": 30,
    "Very fast (20 ms)": 20,
}
CUSTOM_SPEED_LABEL = "Custom"

# Dark, amber-accented palette matching the web app's terminal theme.
BG = "#14110D"
PANEL = "#1C1712"
BORDER = "#34291B"
TEXT = "#EDE6D6"
TEXT_DIM = "#A79C87"
ACCENT = "#E8A33D"
ERROR = "#D9614F"
SUCCESS = "#8CBF6A"


class ToolTip:
    """A small delayed tooltip for a widget, shown on hover."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        if self.tip is not None:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip, text=self.text, background="#2A221A", foreground=TEXT,
            font=("Segoe UI", 9), padx=8, pady=4, relief="solid", borderwidth=1,
        )
        label.pack()

    def _hide(self, _event=None):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class AutoTyperApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.configure(bg=BG)
        self.root.geometry("620x640")
        self.root.minsize(480, 520)

        self.engine = TypingEngine()
        self._ui_queue = queue.Queue()

        self._build_ui()
        self._register_global_hotkeys()
        self.root.after(150, self._poll_status)
        self.root.after(50, self._drain_ui_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if not NATIVE_INPUT_AVAILABLE:
            messagebox.showwarning(
                APP_TITLE,
                "The native Windows keyboard input backend is unavailable "
                "on this system, so typing will not work. Local System "
                "Mode requires Windows.",
            )
        if not KEYBOARD_AVAILABLE:
            messagebox.showwarning(
                APP_TITLE,
                "The 'keyboard' package could not be loaded, so the global "
                "Shift+Z / Shift+X hotkeys are unavailable. You can still "
                "use the on-screen Start/Stop buttons.",
            )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        pad = {"padx": 16}

        header = tk.Label(
            self.root, text="> Universal Auto Typer", fg=ACCENT, bg=BG,
            font=("Consolas", 16, "bold"), anchor="w",
        )
        header.pack(fill="x", pady=(16, 2), **pad)

        sub = tk.Label(
            self.root,
            text="Local System Mode — types into whatever window has focus.",
            fg=TEXT_DIM, bg=BG, font=("Segoe UI", 9), anchor="w",
        )
        sub.pack(fill="x", pady=(0, 12), **pad)

        tk.Label(self.root, text="Text to type", fg=TEXT_DIM, bg=BG,
                  font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", **pad)

        text_frame = tk.Frame(self.root, bg=BORDER)
        text_frame.pack(fill="both", expand=True, padx=16, pady=(4, 10))
        self.text_widget = tk.Text(
            text_frame, wrap="none", undo=True, bg=BG, fg=TEXT,
            insertbackground=TEXT, font=("Consolas", 10), relief="flat",
            padx=10, pady=10,
        )
        self.text_widget.pack(fill="both", expand=True, padx=1, pady=1)

        # Controls row
        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill="x", **pad, pady=(0, 10))

        self.speed_var = tk.StringVar(value="Normal (40 ms)")
        self._labeled(controls, "Speed", 0)
        self.speed_menu = ttk.Combobox(
            controls, textvariable=self.speed_var, state="readonly",
            values=list(SPEED_PRESETS.keys()) + [CUSTOM_SPEED_LABEL], width=16,
        )
        self.speed_menu.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.speed_menu.bind("<<ComboboxSelected>>", self._on_speed_change)

        self._labeled(controls, "Custom (ms)", 1)
        self.custom_delay_var = tk.StringVar(value="15")
        self.custom_delay_entry = tk.Spinbox(
            controls, from_=15, to=1000, textvariable=self.custom_delay_var,
            width=6, bg=PANEL, fg=TEXT, relief="flat",
        )
        self.custom_delay_entry.grid(row=1, column=1, sticky="w", padx=(0, 10))
        self.custom_delay_entry.grid_remove()  # only shown when Speed = Custom

        self._labeled(controls, "Countdown (s)", 2)
        self.countdown_var = tk.StringVar(value="3")
        tk.Spinbox(controls, from_=0, to=60, textvariable=self.countdown_var,
                    width=6, bg=PANEL, fg=TEXT, relief="flat").grid(
            row=1, column=2, sticky="w", padx=(0, 10))

        self._labeled(controls, "Repeat", 3)
        self.repeat_var = tk.StringVar(value="1")
        tk.Spinbox(controls, from_=1, to=100, textvariable=self.repeat_var,
                    width=6, bg=PANEL, fg=TEXT, relief="flat").grid(
            row=1, column=3, sticky="w")

        self.dismiss_popups_var = tk.BooleanVar(value=True)
        dismiss_check = tk.Checkbutton(
            self.root,
            text="Dismiss IDE autocomplete popups before punctuation/spaces (recommended)",
            variable=self.dismiss_popups_var,
            fg=TEXT_DIM, bg=BG, activebackground=BG, activeforeground=TEXT_DIM,
            selectcolor=PANEL, font=("Segoe UI", 8), anchor="w",
        )
        dismiss_check.pack(fill="x", **pad, pady=(4, 0))

        # Buttons row
        btn_row = tk.Frame(self.root, bg=BG)
        btn_row.pack(fill="x", **pad, pady=(0, 6))

        self.start_btn = tk.Button(
            btn_row, text="START TYPING\nShift + Z", command=self._on_start_clicked,
            bg=ACCENT, fg="#1C1712", activebackground="#F0B25A",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=16, pady=8,
            justify="center",
        )
        self.start_btn.pack(side="left", padx=(0, 10))
        ToolTip(self.start_btn, "Start Typing — Shift + Z")

        self.stop_btn = tk.Button(
            btn_row, text="STOP TYPING\nShift + X", command=self._on_stop_clicked,
            bg=BG, fg=ERROR, activebackground="#2A1D18",
            font=("Segoe UI", 10, "bold"), relief="flat", padx=16, pady=8,
            highlightbackground=ERROR, highlightthickness=1,
            justify="center",
        )
        self.stop_btn.pack(side="left")
        ToolTip(self.stop_btn, "Stop Typing — Shift + X")

        hint = tk.Label(
            btn_row, text="Shift + X stops instantly, even mid-countdown",
            fg=TEXT_DIM, bg=BG, font=("Consolas", 9),
        )
        hint.pack(side="left", padx=14)

        # Status
        self.status_var = tk.StringVar(value="> Ready")
        self.status_label = tk.Label(
            self.root, textvariable=self.status_var, fg=TEXT_DIM, bg=BG,
            font=("Consolas", 10), anchor="w",
        )
        self.status_label.pack(fill="x", **pad, pady=(4, 12))

        note = tk.Label(
            self.root,
            text=("Click into your target application before the countdown ends.\n"
                  "Use responsibly. Only automate applications where you have permission to do so."),
            fg="#766B5A", bg=BG, font=("Segoe UI", 8), justify="left", anchor="w",
        )
        note.pack(fill="x", **pad, pady=(0, 14))

    def _labeled(self, parent, text, col):
        tk.Label(parent, text=text, fg=TEXT_DIM, bg=BG,
                  font=("Segoe UI", 8, "bold")).grid(row=0, column=col, sticky="w")

    def _on_speed_change(self, _event=None):
        if self.speed_var.get() == CUSTOM_SPEED_LABEL:
            self.custom_delay_entry.grid()
        else:
            self.custom_delay_entry.grid_remove()

    # ------------------------------------------------------------------
    # Hotkeys (global — fire even when another app has focus)
    # ------------------------------------------------------------------

    def _register_global_hotkeys(self):
        # Shift+X (stop) is already registered globally by the TypingEngine
        # itself (see auto_typer.py) the moment it's constructed, so every
        # consumer — this app and the Flask app's own local mode — shares
        # one consistent global stop hotkey. Registering it a second time
        # here would just fire two overlapping stop handlers on every
        # press, so this app only needs to add its own Shift+Z start hotkey
        # on top of that.
        if not KEYBOARD_AVAILABLE:
            return
        try:
            # suppress=True stops the physical keys from reaching whatever
            # app currently has focus, so "Z" is never typed there.
            keyboard.add_hotkey("shift+z", self._queue_start, suppress=True)
        except Exception as exc:
            print(f"Could not register global hotkeys: {exc}")

    def _queue_start(self):
        # Hotkey callbacks run on the `keyboard` library's own listener
        # thread, not Tkinter's main thread, so we hand off through a
        # queue and let the main-loop poller do the actual Tk work.
        self._ui_queue.put("start")

    def _drain_ui_queue(self):
        try:
            while True:
                action = self._ui_queue.get_nowait()
                if action == "start":
                    self._start_typing()
        except queue.Empty:
            pass
        self.root.after(50, self._drain_ui_queue)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_start_clicked(self):
        self._start_typing()

    def _on_stop_clicked(self):
        self.engine.stop()

    def _start_typing(self):
        text = self.text_widget.get("1.0", "end-1c")
        if not text:
            self.status_var.set("> Enter some text first.")
            return

        if self.speed_var.get() == CUSTOM_SPEED_LABEL:
            try:
                delay_ms = max(0, min(1000, int(self.custom_delay_var.get())))
            except ValueError:
                delay_ms = 5
        else:
            delay_ms = SPEED_PRESETS.get(self.speed_var.get(), 40)
        try:
            countdown = max(0, min(60, int(self.countdown_var.get())))
        except ValueError:
            countdown = 3
        try:
            repeat = max(1, min(100, int(self.repeat_var.get())))
        except ValueError:
            repeat = 1

        started = self.engine.start(text=text, delay_ms=delay_ms,
                                      countdown=countdown, repeat=repeat,
                                      dismiss_popups=self.dismiss_popups_var.get())
        if not started:
            self.status_var.set("> A typing job is already running.")

    # ------------------------------------------------------------------
    # Status polling
    # ------------------------------------------------------------------

    def _poll_status(self):
        s = self.engine.get_status()
        status = s["status"]

        if status == "counting":
            self.status_var.set(f"> Starting in {s['countdownRemaining']}...")
            self.status_label.configure(fg=ACCENT)
        elif status == "typing":
            suffix = f" ({s['currentRepeat']} / {s['totalRepeats']})" if s["totalRepeats"] > 1 else ""
            self.status_var.set(
                f"> Typing{suffix} — {s['charsTyped']} / {s['charsTotal']} characters"
            )
            self.status_label.configure(fg=ACCENT)
        elif status == "done":
            self.status_var.set("> Finished.")
            self.status_label.configure(fg=SUCCESS)
        elif status == "stopped":
            self.status_var.set(f"> {s['message']}")
            self.status_label.configure(fg=ERROR)
        elif status == "error":
            self.status_var.set(f"> {s['message']}")
            self.status_label.configure(fg=ERROR)
        else:
            self.status_var.set("> Ready")
            self.status_label.configure(fg=TEXT_DIM)

        self.root.after(150, self._poll_status)

    def _on_close(self):
        self.engine.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    AutoTyperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
