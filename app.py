"""
Universal Auto Typer - Flask backend

Serves the web UI and exposes a small API used by the "Local System" mode
to drive the local desktop-typing engine (auto_typer.py).

IMPORTANT:
The Local System mode only works when this server is running on the
user's own machine (via run.bat). A deployed/online copy of this app
(e.g. on Render) can only ever offer the Browser mode, because a web
server has no access to a visitor's physical keyboard or desktop.
"""

import os
import logging

from flask import Flask, render_template, request, jsonify

from auto_typer import TypingEngine, NATIVE_INPUT_AVAILABLE

# --------------------------------------------------------------------------
# App setup
# --------------------------------------------------------------------------

app = Flask(__name__)

# Keep Flask's own logging quiet-ish in production; don't leak internals.
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("universal-auto-typer")

# A single shared typing engine instance. The app is intended for one
# local user at a time (this is a local desktop-automation tool, not a
# multi-tenant service), so a single global engine is sufficient and
# avoids the complexity of per-session engines.
engine = TypingEngine()


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------

def _clamp_int(value, minimum, maximum, default):
    """Safely coerce a value to an int within [minimum, maximum]."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, n))


def _parse_start_payload(data):
    """
    Validate and normalize the JSON payload for /api/start.
    Returns (params_dict, error_message). error_message is None on success.
    """
    if not isinstance(data, dict):
        return None, "Invalid request body."

    text = data.get("text", "")
    if not isinstance(text, str):
        return None, "Text must be a string."
    if text == "":
        return None, "Please enter some text to type."

    # Delay in milliseconds per character. 0ms (Custom) .. 5000ms is a sane range.
    delay_ms = _clamp_int(data.get("delayMs", 40), 0, 5000, 40)

    # Countdown in seconds before typing starts.
    countdown = _clamp_int(data.get("countdown", 3), 0, 60, 3)

    # Number of times to repeat the full text.
    repeat = _clamp_int(data.get("repeat", 1), 1, 100, 1)

    # Whether to send Escape before a word-boundary character (space,
    # punctuation, newline) right after an identifier/keyword, to close
    # any IDE autocomplete popup that might otherwise intercept it.
    dismiss_popups = bool(data.get("dismissPopups", True))

    return {
        "text": text,
        "delay_ms": delay_ms,
        "countdown": countdown,
        "repeat": repeat,
        "dismiss_popups": dismiss_popups,
    }, None


# --------------------------------------------------------------------------
# Page routes
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", native_input_available=NATIVE_INPUT_AVAILABLE)


# --------------------------------------------------------------------------
# API routes - Local System typing engine
# --------------------------------------------------------------------------

@app.route("/api/start", methods=["POST"])
def api_start():
    if not NATIVE_INPUT_AVAILABLE:
        return jsonify({
            "ok": False,
            "error": (
                "Local typing is unavailable on this server. "
                "The native Windows keyboard backend requires Windows "
                "(this is expected on a deployed/online copy of the app "
                "or a non-Windows machine). Use Browser mode instead."
            ),
        }), 400

    data = request.get_json(silent=True)
    params, error = _parse_start_payload(data)
    if error:
        return jsonify({"ok": False, "error": error}), 400

    started = engine.start(
        text=params["text"],
        delay_ms=params["delay_ms"],
        countdown=params["countdown"],
        repeat=params["repeat"],
        dismiss_popups=params["dismiss_popups"],
    )

    if not started:
        return jsonify({
            "ok": False,
            "error": "A typing job is already running. Stop it first.",
        }), 409

    return jsonify({"ok": True, "status": engine.get_status()})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    engine.stop()
    return jsonify({"ok": True, "status": engine.get_status()})


@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({"ok": True, "status": engine.get_status()})


# --------------------------------------------------------------------------
# Error handlers - never leak raw stack traces to the client
# --------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(_err):
    return jsonify({"ok": False, "error": "Not found."}), 404


@app.errorhandler(500)
def server_error(_err):
    log.exception("Unhandled server error")
    return jsonify({"ok": False, "error": "Something went wrong on the server."}), 500


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

if __name__ == "__main__":
    # Local development: http://127.0.0.1:5000
    # Deployment (Docker/Render, etc.): bind 0.0.0.0 and use the
    # platform-provided PORT, falling back to 5000 for local runs.
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
