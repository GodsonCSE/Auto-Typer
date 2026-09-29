/* ==========================================================================
   Universal Auto Typer — frontend logic

   Two independent typing paths:
     - Browser mode:  runs entirely in this tab, reproduces the text into
                       the on-page output panel. Works everywhere, including
                       a deployed/online copy of the app.
     - Local mode:    calls the Flask API, which drives the native Windows
                       keyboard backend on the machine the server is
                       running on. Only meaningful when this app is
                       running locally on Windows (run.bat).

   The user's input text is never trimmed, reformatted, or re-indented —
   it is read straight from the textarea and used character-for-character.
   ========================================================================== */

(function () {
  "use strict";

  // ---- Elements -----------------------------------------------------

  const inputText      = document.getElementById("inputText");
  const inputField      = document.getElementById("inputField");
  const fullscreenBtn  = document.getElementById("fullscreenBtn");
  const charCountEl     = document.getElementById("charCount");
  const lineCountEl     = document.getElementById("lineCount");
  const clearBtn         = document.getElementById("clearBtn");

  const modeBrowserBtn  = document.getElementById("modeBrowserBtn");
  const modeLocalBtn    = document.getElementById("modeLocalBtn");
  const modeNote         = document.getElementById("modeNote");
  const localWarning    = document.getElementById("localWarning");
  const dismissPopupsCheckbox = document.getElementById("dismissPopups");
  const outputField      = document.getElementById("outputField");
  const outputArea       = document.getElementById("outputArea");
  const clearOutputBtn  = document.getElementById("clearOutputBtn");

  const speedSelect      = document.getElementById("speedSelect");
  const customDelayField = document.getElementById("customDelayField");
  const customDelay      = document.getElementById("customDelay");

  const repeatSelect     = document.getElementById("repeatSelect");
  const customRepeatField = document.getElementById("customRepeatField");
  const customRepeat     = document.getElementById("customRepeat");

  const countdownInput  = document.getElementById("countdownInput");

  const startBtn          = document.getElementById("startBtn");
  const stopBtn            = document.getElementById("stopBtn");
  const statusLine        = document.querySelector(".status-line");
  const statusText        = document.getElementById("statusText");
  const progressContainer = document.getElementById("progressContainer");
  const progressBar        = document.getElementById("progressBar");
  const progressPercent   = document.getElementById("progressPercent");

  const MODE_NOTES = {
    browser: "Demonstrates the typing animation right here in this tab. Works anywhere this page is open, including the deployed website.",
    local: "",
  };

  let mode = "browser"; // "browser" | "local"

  // Browser-mode run state
  let browserRunId = 0;      // increments to invalidate an in-flight run
  let browserRunning = false;

  // Local-mode poll state
  let localPollHandle = null;

  // ---- Character / line count ---------------------------------------

  function updateCounts() {
    const value = inputText.value;
    const chars = value.length;
    const lines = value.length === 0 ? 1 : value.split("\n").length;
    charCountEl.textContent = "Characters: " + chars.toLocaleString();
    lineCountEl.textContent = "Lines: " + lines.toLocaleString();
  }

  inputText.addEventListener("input", updateCounts);
  updateCounts();

  clearBtn.addEventListener("click", function () {
    if (browserRunning || stopBtn.disabled === false) return; // don't clear mid-run
    inputText.value = "";
    updateCounts();
    inputText.focus();
  });

  // "Clear output" only empties the output panel — it never touches the
  // input textarea, and clearing one never affects the other.
  clearOutputBtn.addEventListener("click", function () {
    if (browserRunning || stopBtn.disabled === false) return; // don't clear mid-run
    outputArea.textContent = "";
  });

  // ---- Full-screen editing for the input textarea ----------------------

  function setFullscreen(on) {
    inputField.classList.toggle("fullscreen", on);
    document.body.classList.toggle("fullscreen-active", on);
    fullscreenBtn.innerHTML = on
      ? '<i class="fa-solid fa-compress"></i> Exit full screen'
      : '<i class="fa-solid fa-expand"></i> Full screen';
    if (on) inputText.focus();
  }

  fullscreenBtn.addEventListener("click", function () {
    setFullscreen(!inputField.classList.contains("fullscreen"));
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && inputField.classList.contains("fullscreen")) {
      setFullscreen(false);
    }
  });

  // ---- Speed / delay ---------------------------------------------------

  function getDelayMs() {
    if (speedSelect.value === "custom") {
      return clampInt(customDelay.value, 0, 1000, 5);
    }
    return clampInt(speedSelect.value, 0, 1000, 40);
  }

  speedSelect.addEventListener("change", function () {
    customDelayField.hidden = speedSelect.value !== "custom";
  });

  // ---- Repeat -----------------------------------------------------------

  function getRepeatCount() {
    if (repeatSelect.value === "custom") {
      return clampInt(customRepeat.value, 1, 100, 1);
    }
    return clampInt(repeatSelect.value, 1, 100, 1);
  }

  repeatSelect.addEventListener("change", function () {
    customRepeatField.hidden = repeatSelect.value !== "custom";
  });

  function clampInt(value, min, max, fallback) {
    const n = parseInt(value, 10);
    if (isNaN(n)) return fallback;
    return Math.max(min, Math.min(max, n));
  }

  // ---- Mode switch --------------------------------------------------

  function setMode(newMode) {
    if (isRunning()) return; // don't allow switching mid-run
    mode = newMode;
    const isLocal = mode === "local";

    modeBrowserBtn.classList.toggle("active", !isLocal);
    modeBrowserBtn.setAttribute("aria-selected", String(!isLocal));
    modeLocalBtn.classList.toggle("active", isLocal);
    modeLocalBtn.setAttribute("aria-selected", String(isLocal));

    const note = MODE_NOTES[mode];
    modeNote.textContent = note;
    modeNote.hidden = !note;
    localWarning.hidden = !isLocal;
    outputField.hidden = isLocal;
  }

  modeBrowserBtn.addEventListener("click", function () { setMode("browser"); });
  modeLocalBtn.addEventListener("click", function () { setMode("local"); });

  // ---- Status helpers -------------------------------------------------

  function setStatus(text, kind) {
    statusText.textContent = text;
    // classList.toggle rather than overwriting className wholesale, so the
    // layout/utility classes already on this element (Tailwind spacing,
    // borders, etc.) survive every status update.
    statusLine.classList.remove("is-typing", "is-done", "is-stopped", "is-error");
    if (kind) statusLine.classList.add("is-" + kind);
    updateProgressForStatus(kind);
  }

  // ---- Progress bar (purely cosmetic - reflects real typing progress) --

  function setProgress(percent) {
    if (!progressBar || !progressPercent) return;
    const clamped = Math.max(0, Math.min(100, Math.round(percent)));
    progressBar.style.width = clamped + "%";
    progressPercent.textContent = clamped + "%";
  }

  function showProgress() {
    if (!progressContainer) return;
    progressContainer.classList.remove("hidden");
    progressContainer.classList.add("flex");
  }

  function hideProgress() {
    if (!progressContainer) return;
    progressContainer.classList.add("hidden");
    progressContainer.classList.remove("flex");
    setProgress(0);
  }

  function updateProgressForStatus(kind) {
    if (kind === "typing") {
      showProgress();
    } else {
      hideProgress();
    }
  }

  function isRunning() {
    return browserRunning || !stopBtn.disabled;
  }

  function setRunningUI(running) {
    startBtn.disabled = running;
    stopBtn.disabled = !running;
    modeBrowserBtn.disabled = running;
    modeLocalBtn.disabled = running;
  }

  // ---- Start / Stop -------------------------------------------------

  startBtn.addEventListener("click", function () {
    const text = inputText.value;
    if (text.length === 0) {
      setStatus("Enter some text first.", "error");
      return;
    }
    if (mode === "browser") {
      startBrowserTyping(text);
    } else {
      startLocalTyping(text);
    }
  });

  stopBtn.addEventListener("click", function () {
    if (mode === "browser") {
      stopBrowserTyping();
    } else {
      stopLocalTyping();
    }
  });

  // ======================================================================
  // Browser mode
  // ======================================================================

  function startBrowserTyping(text) {
    const delayMs = getDelayMs();
    const countdown = clampInt(countdownInput.value, 0, 60, 3);
    const repeat = getRepeatCount();

    browserRunId += 1;
    const runId = browserRunId;
    browserRunning = true;
    setRunningUI(true);
    outputArea.textContent = "";

    runBrowserCountdown(runId, countdown, function () {
      runBrowserTyping(runId, text, delayMs, repeat);
    });
  }

  function stopBrowserTyping() {
    browserRunId += 1; // invalidates any in-flight timers
    browserRunning = false;
    setRunningUI(false);
    setStatus("Stopped by user.", "stopped");
    removeCursor();
  }

  function runBrowserCountdown(runId, seconds, onDone) {
    if (seconds <= 0) {
      setStatus("Typing...", "typing");
      onDone();
      return;
    }
    let remaining = seconds;
    setStatus("Starting in " + remaining + "...", "typing");
    const tick = function () {
      if (runId !== browserRunId) return;
      remaining -= 1;
      if (remaining <= 0) {
        setStatus("Typing...", "typing");
        onDone();
        return;
      }
      setStatus("Starting in " + remaining + "...", "typing");
      setTimeout(tick, 1000);
    };
    setTimeout(tick, 1000);
  }

  function runBrowserTyping(runId, text, delayMs, totalRepeats) {
    let repeat = 1;

    function typeOneRepeat(onRepeatDone) {
      let i = 0;
      outputArea.textContent = "";
      appendCursor();

      function step() {
        if (runId !== browserRunId) return; // stopped
        if (i >= text.length) {
          onRepeatDone();
          return;
        }
        insertBeforeCursor(text[i]);
        i += 1;
        const overallDone = (repeat - 1) * text.length + i;
        setProgress((overallDone / (text.length * totalRepeats)) * 100);
        setTimeout(step, delayMs);
      }
      step();
    }

    function nextRepeat() {
      if (runId !== browserRunId) return;
      if (repeat > totalRepeats) {
        browserRunning = false;
        setRunningUI(false);
        setStatus("Finished.", "done");
        removeCursor();
        return;
      }
      if (totalRepeats > 1) {
        setStatus("Typing (" + repeat + " / " + totalRepeats + ")...", "typing");
      }
      typeOneRepeat(function () {
        repeat += 1;
        nextRepeat();
      });
    }

    nextRepeat();
  }

  function appendCursor() {
    const span = document.createElement("span");
    span.className = "typing-cursor";
    span.textContent = "\u00A0";
    outputArea.appendChild(span);
  }

  function insertBeforeCursor(char) {
    const cursor = outputArea.querySelector(".typing-cursor");
    const textNode = document.createTextNode(char);
    if (cursor) {
      outputArea.insertBefore(textNode, cursor);
    } else {
      outputArea.appendChild(textNode);
    }
    outputArea.scrollTop = outputArea.scrollHeight;
  }

  function removeCursor() {
    const cursor = outputArea.querySelector(".typing-cursor");
    if (cursor) cursor.remove();
  }

  // ======================================================================
  // Local mode
  // ======================================================================

  function startLocalTyping(text) {
    const delayMs = getDelayMs();
    const countdown = clampInt(countdownInput.value, 0, 60, 3);
    const repeat = getRepeatCount();

    setRunningUI(true);
    setStatus("Starting...", "typing");

    fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        delayMs: delayMs,
        countdown: countdown,
        repeat: repeat,
        dismissPopups: dismissPopupsCheckbox.checked,
      }),
    })
      .then(function (res) { return res.json().then(function (body) { return { res: res, body: body }; }); })
      .then(function (result) {
        if (!result.res.ok || !result.body.ok) {
          setStatus(result.body.error || "Could not start typing.", "error");
          setRunningUI(false);
          return;
        }
        pollLocalStatus();
      })
      .catch(function () {
        setStatus("Could not reach the server.", "error");
        setRunningUI(false);
      });
  }

  function stopLocalTyping() {
    fetch("/api/stop", { method: "POST" }).catch(function () { /* best-effort */ });
  }

  function pollLocalStatus() {
    if (localPollHandle) clearTimeout(localPollHandle);

    fetch("/api/status")
      .then(function (res) { return res.json(); })
      .then(function (body) {
        if (!body.ok) {
          setStatus("Lost contact with the server.", "error");
          setRunningUI(false);
          return;
        }
        const s = body.status;
        renderLocalStatus(s);

        if (s.status === "counting" || s.status === "typing") {
          localPollHandle = setTimeout(pollLocalStatus, 200);
        } else {
          setRunningUI(false);
        }
      })
      .catch(function () {
        setStatus("Lost contact with the server.", "error");
        setRunningUI(false);
      });
  }

  function renderLocalStatus(s) {
    if (s.status === "counting") {
      setStatus("Starting in " + s.countdownRemaining + "... click your target window now.", "typing");
    } else if (s.status === "typing") {
      const repeatSuffix = s.totalRepeats > 1 ? " (" + s.currentRepeat + " / " + s.totalRepeats + ")" : "";
      setStatus("Typing" + repeatSuffix + " \u2014 " + s.charsTyped + " / " + s.charsTotal + " characters", "typing");
      if (s.charsTotal > 0) setProgress((s.charsTyped / s.charsTotal) * 100);
    } else if (s.status === "done") {
      setStatus("Finished.", "done");
    } else if (s.status === "stopped") {
      setStatus(s.message || "Stopped.", "stopped");
    } else if (s.status === "error") {
      setStatus(s.message || "An error occurred.", "error");
    } else {
      setStatus(s.message || "Ready", null);
    }
  }

  // ---- Hotkeys: Shift+Z (start) / Shift+X (stop) -----------------------
  //
  // These mirror the Start/Stop buttons on this page. They intentionally
  // do nothing while focus is in the text box or a form control, so
  // typing a literal "Z" or "X" into your text is never hijacked. For a
  // hotkey that works globally — even while a different application has
  // focus — use the standalone Local System Mode app (see build.bat).

  function isFormField(el) {
    if (!el) return false;
    const tag = el.tagName;
    return tag === "TEXTAREA" || tag === "INPUT" || tag === "SELECT" || el.isContentEditable;
  }

  document.addEventListener("keydown", function (event) {
    if (!event.shiftKey || isFormField(document.activeElement)) return;

    const key = event.key.toLowerCase();
    if (key === "z") {
      event.preventDefault();
      if (!startBtn.disabled) startBtn.click();
    } else if (key === "x") {
      event.preventDefault();
      if (!stopBtn.disabled) stopBtn.click();
    }
  });

  // ---- Theme switcher ---------------------------------------------------
  //
  // Exposed on window since the theme swatches use inline onclick="" in
  // the HTML. Purely cosmetic - never touches typing logic or state.

  const THEME_STORAGE_KEY = "universalAutoTyperTheme";

  function markActiveSwatch(theme) {
    document.querySelectorAll(".theme-swatch[data-theme-swatch]").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-theme-swatch") === theme);
    });
  }

  window.setTheme = function (theme) {
    document.documentElement.setAttribute("data-theme", theme);
    markActiveSwatch(theme);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (e) {
      // localStorage unavailable (private browsing, etc.) - theme just
      // won't persist across reloads, which is a fine fallback.
    }
  };

  function initTheme() {
    let saved = null;
    try {
      saved = localStorage.getItem(THEME_STORAGE_KEY);
    } catch (e) {
      // ignore
    }
    const theme = saved || "emerald";
    document.documentElement.setAttribute("data-theme", theme);
    markActiveSwatch(theme);
  }

  // ---- Init -----------------------------------------------------------

  initTheme();
  setMode("browser");
  setStatus("Ready", null);
})();
