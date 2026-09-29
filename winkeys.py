"""
Universal Auto Typer - Windows-native keyboard input backend

Replaces the previous pyautogui.write()-per-character approach with direct
calls to the Win32 SendInput API via ctypes. This is the same low-level
mechanism the operating system itself uses to inject keyboard input, so it
avoids the per-call Python/automation-library overhead that made the old
Local System Mode noticeably slower than Browser Mode.

Two kinds of key events are generated:

  - Standard characters that exist on the active Windows keyboard layout
    (letters, digits, and the punctuation/symbols normal code uses) are
    sent as *real virtual-key events*, resolved via the Win32 VkKeyScanW
    API - the same lookup Windows itself uses to know "what key (plus
    Shift/Ctrl/Alt if needed) produces this character on this layout."
    Each character therefore gets its own distinct virtual-key code, just
    like a real keyboard.
  - Characters VkKeyScanW can't map on the current layout (most non-Latin
    scripts, emoji, symbols outside the layout) fall back to the
    KEYEVENTF_UNICODE flag, which tells Windows "deliver exactly this
    Unicode character" directly, bypassing key/scan-code translation.

  The VK-based path is the default (rather than KEYEVENTF_UNICODE for
  everything) for a specific reason: every KEYEVENTF_UNICODE event uses
  wVk = 0, because there's no virtual key to report - and Windows tracks
  "is this key currently held down" (for its own auto-repeat handling)
  primarily by virtual-key code. When every character in a fast sequence
  shares wVk = 0, that tracking can occasionally get confused about which
  "vk=0 press" is still active, producing a burst of a repeated character
  that was never actually repeated in the input text (e.g. "{" typed once
  coming out as "{{{{"). Giving each character its own real virtual key
  avoids that ambiguity entirely, the same way it doesn't happen when you
  type on a physical keyboard.

  - Enter and Tab are sent as real virtual-key events (VK_RETURN / VK_TAB)
    instead of synthesized Unicode characters, because many editors (IDEs
    in particular) key their auto-indent / focus-change / newline
    behavior off the actual key event, not off a WM_CHAR for U+000D or
    U+0009. Sending the real key preserves that behavior.

Each character's key-down and key-up are sent as two *separate* SendInput()
calls with a tiny settle gap between them (and after), rather than being
batched into one atomic call. This matters: KEYEVENTF_UNICODE input goes
through Windows' message-translation layer (VK_PACKET -> WM_CHAR), and if
the next character's key-down arrives before that translation has actually
happened, the pending character data can be overwritten before the target
window reads it - producing exactly the kind of corruption ("obj" typed as
"bbj", "new" typed as "nnnew") this project hit with typing sent too fast.
The settle gap gives the receiving application's message loop a chance to
process each keystroke before the next one is injected, and applies as a
floor under every speed setting - even "Very fast" or a Custom delay of 0.

This module only does anything on Windows. On any other platform (e.g.
this project's Docker/deployed copy, or a developer's Mac/Linux machine),
NATIVE_INPUT_AVAILABLE is False and every function is a safe no-op-free
import - callers are expected to check the flag first.
"""

import sys
import time
import ctypes
import logging

log = logging.getLogger("universal-auto-typer.winkeys")

NATIVE_INPUT_AVAILABLE = False

# Minimum gap (seconds) enforced between a key's down and up event, and
# again before the next character's down event. This is a floor under
# whatever per-character delay the UI is configured with - it exists
# purely for correctness, so it applies even at the fastest speed
# setting or a Custom delay of 0ms. Raised to 8ms: at 5ms the Win32
# message loop occasionally hadn't finished translating a Shift+key or
# VK_PACKET event before the next key-down arrived, producing symptoms
# like 'boolean' typed as 'Boolean' (Shift bleeding) or 'util.;' typed
# as 'util.8' (symbol lookup racing with the previous key-up). 8ms
# gives the receiving application's message loop enough headroom to
# fully process each event before the next one is injected, while still
# supporting a real inter-character pace of 15 ms.
_KEY_SETTLE_SECONDS = 0.008

# Virtual-key codes used for the handful of "real key" cases.
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12       # Alt
VK_LWIN = 0x5B
VK_RWIN = 0x5C

if sys.platform.startswith("win"):
    try:
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)

        INPUT_KEYBOARD = 1

        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002
        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_SCANCODE = 0x0008

        ULONG_PTR = ctypes.c_size_t

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = (
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            )

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = (
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            )

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = (
                ("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD),
            )

        class _INPUTUNION(ctypes.Union):
            # All three members are declared (even though we only ever
            # populate `ki`) so this union's size matches the real Win32
            # INPUT struct exactly. SendInput rejects calls whose cbSize
            # doesn't match its own idea of sizeof(INPUT), and a union
            # that only contained KEYBDINPUT would come out smaller.
            _fields_ = (
                ("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT),
            )

        class INPUT(ctypes.Structure):
            _anonymous_ = ("u",)
            _fields_ = (
                ("type", wintypes.DWORD),
                ("u", _INPUTUNION),
            )

        LPINPUT = ctypes.POINTER(INPUT)

        user32.SendInput.argtypes = (wintypes.UINT, LPINPUT, ctypes.c_int)
        user32.SendInput.restype = wintypes.UINT

        # VkKeyScanW(ch) -> low byte: virtual-key code; high byte: shift
        # state (bit0=Shift, bit1=Ctrl, bit2=Alt needed to produce ch on
        # the active keyboard layout). Returns -1 (0xFFFF) if the active
        # layout has no key that produces this character at all.
        user32.VkKeyScanW.argtypes = (wintypes.WCHAR,)
        user32.VkKeyScanW.restype = ctypes.c_short

        NATIVE_INPUT_AVAILABLE = True

    except Exception as exc:  # pragma: no cover - depends on host environment
        log.warning("Windows SendInput backend unavailable: %s", exc)
        NATIVE_INPUT_AVAILABLE = False


# --------------------------------------------------------------------------
# Public API - all functions below are only safe to call when
# NATIVE_INPUT_AVAILABLE is True.
# --------------------------------------------------------------------------

def _send(inp):
    """Submit a single INPUT struct to Windows."""
    arr = (INPUT * 1)(inp)
    sent = user32.SendInput(1, arr, ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error())


def _unicode_event(code_unit, key_up):
    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if key_up else 0)
    ki = KEYBDINPUT(0, code_unit, flags, 0, 0)
    return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=ki))


def _vk_event(vk, key_up):
    flags = KEYEVENTF_KEYUP if key_up else 0
    ki = KEYBDINPUT(vk, 0, flags, 0, 0)
    return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=ki))


def _press(down_event, up_event):
    """
    Send a key-down then a key-up as two separate calls, with a small
    settle gap on both sides. See _KEY_SETTLE_SECONDS above for why this
    matters for correctness, not just pacing.
    """
    _send(down_event)
    time.sleep(_KEY_SETTLE_SECONDS)
    _send(up_event)
    time.sleep(_KEY_SETTLE_SECONDS)


def _resolve_vk(char):
    """
    Look up the (vk, needs_shift, needs_ctrl, needs_alt) needed to produce
    `char` on the active keyboard layout, or None if this layout has no
    key that produces it (caller should fall back to KEYEVENTF_UNICODE).
    Only meaningful for a single UTF-16 code unit - callers should not
    call this for characters requiring a surrogate pair.
    """
    try:
        result = user32.VkKeyScanW(char)
    except Exception:
        return None
    if result == -1:
        return None
    vk = result & 0xFF
    shift_state = (result >> 8) & 0xFF
    # Reject results where the VK or shift-state bytes are nonsensical:
    # vk=0xFF means "no key", shift_state > 0x07 means undefined modifier
    # bits are set (e.g. AltGr-only or dead-key characters on some layouts).
    # Both would produce wrong modifier presses; fall back to KEYEVENTF_UNICODE.
    if vk == 0xFF or shift_state > 0x07:
        return None
    return vk, bool(shift_state & 1), bool(shift_state & 2), bool(shift_state & 4)


def _type_vk_with_modifiers(vk, need_shift, need_ctrl, need_alt):
    """
    Press vk with whichever of Shift/Ctrl/Alt this character needs held
    down, then release them in reverse order. Each individual key gets
    its own real virtual-key code, so - unlike KEYEVENTF_UNICODE, where
    every character shares wVk=0 - Windows' own key-repeat tracking can't
    confuse this character's key with any other.
    """
    try:
        if need_shift:
            _send(_vk_event(VK_SHIFT, False))
            time.sleep(_KEY_SETTLE_SECONDS)
        if need_ctrl:
            _send(_vk_event(VK_CONTROL, False))
            time.sleep(_KEY_SETTLE_SECONDS)
        if need_alt:
            _send(_vk_event(VK_MENU, False))
            time.sleep(_KEY_SETTLE_SECONDS)

        _press(_vk_event(vk, False), _vk_event(vk, True))

        if need_alt:
            _send(_vk_event(VK_MENU, True))
            time.sleep(_KEY_SETTLE_SECONDS)
        if need_ctrl:
            _send(_vk_event(VK_CONTROL, True))
            time.sleep(_KEY_SETTLE_SECONDS)
        if need_shift:
            _send(_vk_event(VK_SHIFT, True))
            time.sleep(_KEY_SETTLE_SECONDS)
        return True
    except Exception as exc:
        log.warning("Could not send virtual key %r: %s", vk, exc)
        return False


def type_char(char):
    """
    Inject a single character into whatever window currently has
    keyboard focus. Returns True on success, False if this character
    could not be sent (caller may choose to log/skip it).
    """
    if char == "\n":
        return _type_vk(VK_RETURN)
    if char == "\t":
        return _type_vk(VK_TAB)

    # Prefer a real virtual-key event when this character fits in one
    # UTF-16 code unit and the active keyboard layout can produce it -
    # see the module docstring for why this is preferred over
    # KEYEVENTF_UNICODE whenever possible.
    if len(char.encode("utf-16-le", errors="ignore")) == 2:
        mapping = _resolve_vk(char)
        if mapping is not None:
            return _type_vk_with_modifiers(*mapping)

    # Fallback: KEYEVENTF_UNICODE, for characters this layout has no key
    # for (most non-Latin scripts, emoji, symbols outside the layout).
    # Encode as UTF-16 so characters outside the Basic Multilingual Plane
    # are correctly split into the surrogate pair Windows expects - each
    # 16-bit code unit is sent as its own key-down/key-up pair, exactly
    # reproducing the character.
    try:
        code_units = char.encode("utf-16-le")
    except Exception as exc:
        log.warning("Could not encode character %r: %s", char, exc)
        return False

    try:
        for i in range(0, len(code_units), 2):
            unit = code_units[i] | (code_units[i + 1] << 8)
            _press(_unicode_event(unit, False), _unicode_event(unit, True))
        return True
    except Exception as exc:
        log.warning("Could not send character %r: %s", char, exc)
        return False


def _type_vk(vk):
    try:
        _press(_vk_event(vk, False), _vk_event(vk, True))
        return True
    except Exception as exc:
        log.warning("Could not send key %r: %s", vk, exc)
        return False


def press_escape():
    """
    Send a real Escape key press. Used to dismiss an editor's
    autocomplete/suggestion popup before typing a character that could
    otherwise be intercepted by it (accepting a suggestion instead of
    being typed literally) - see TypingEngine's word-boundary logic in
    auto_typer.py. A no-op in a plain text field, so it's safe to send
    even when no popup is actually open.
    """
    return _type_vk(VK_ESCAPE)


def release_modifiers():
    """
    Force Shift/Ctrl/Alt/Win key-up events. Printable characters never
    hold a modifier down in the first place (KEYEVENTF_UNICODE needs no
    Shift simulation), so this is mainly a safety net for Shift+X being
    pressed mid-keystroke by the user themselves.
    """
    if not NATIVE_INPUT_AVAILABLE:
        return
    for vk in (VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN):
        try:
            _send(_vk_event(vk, True))
        except Exception:
            pass
