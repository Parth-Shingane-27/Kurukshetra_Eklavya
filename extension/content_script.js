// Runs ONLY when background.js has already confirmed this page's URL carries our own
// `asbo_session` marker (see background.js) — there is no code path that reaches this file on
// a page opened any other way. Guarded again here so a second execution (e.g. SPA
// client-side navigation re-triggering onCommitted) doesn't double-inject the UI.
(async function asboFormAssistant() {
  if (window.__asboAssistantLoaded) return;
  window.__asboAssistantLoaded = true;

  // Dev default — a production build would read this from chrome.storage, set by the popup's
  // options, rather than hardcoding one backend. Documented as a known limitation (README).
  const API_BASE_URL = "http://localhost:8000";

  const params = new URL(window.location.href).searchParams;
  const sessionId = params.get("asbo_session");
  if (!sessionId) return;

  const origin = window.location.origin;

  let assistanceToken = null;
  let schemeName = null;

  async function validate() {
    const res = await fetch(`${API_BASE_URL}/api/assistance/validate-session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, origin }),
    });
    return res.json();
  }

  function injectStyles() {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = chrome.runtime.getURL("injected_styles.css");
    document.documentElement.appendChild(link);
  }

  function showInactiveBanner(reason) {
    const banner = document.createElement("div");
    banner.className = "asbo-banner asbo-banner-inactive";
    banner.textContent = `ASBO form assistance is not available on this page: ${reason}`;
    const close = document.createElement("button");
    close.textContent = "✕";
    close.className = "asbo-banner-close";
    close.onclick = () => banner.remove();
    banner.appendChild(close);
    document.documentElement.appendChild(banner);
    setTimeout(() => banner.remove(), 8000);
  }

  // --- Best-effort form context extraction (Section 11) ------------------------------------
  // Only ever runs on an explicit user text selection, never continuously (Section 7/8).
  function nearestLabelFor(node) {
    let el = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    for (let i = 0; i < 6 && el; i++, el = el.parentElement) {
      const label = el.querySelector?.("label") || (el.tagName === "LABEL" ? el : null);
      if (label && label.textContent.trim()) return label.textContent.trim().slice(0, 200);
    }
    return null;
  }

  function nearestOptionsFor(node) {
    let el = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    for (let i = 0; i < 6 && el; i++, el = el.parentElement) {
      const select = el.querySelector?.("select");
      if (select) {
        return Array.from(select.options)
          .map((o) => o.textContent.trim())
          .filter(Boolean)
          .slice(0, 15);
      }
      const radios = el.querySelectorAll?.('input[type="radio"], input[type="checkbox"]');
      if (radios && radios.length) {
        return Array.from(radios)
          .map((r) => r.closest("label")?.textContent.trim() || r.value)
          .filter(Boolean)
          .slice(0, 15);
      }
    }
    return [];
  }

  // --- Floating help button + explanation panel ---------------------------------------------
  let helpButton = null;
  let currentSelectionText = null;
  let currentFieldLabel = null;
  let currentOptions = [];

  function hideHelpButton() {
    if (helpButton) {
      helpButton.remove();
      helpButton = null;
    }
  }

  function showHelpButtonNear(rect) {
    hideHelpButton();
    helpButton = document.createElement("button");
    helpButton.className = "asbo-help-button";
    helpButton.textContent = "🛟 Explain this";
    helpButton.style.top = `${window.scrollY + rect.bottom + 6}px`;
    helpButton.style.left = `${window.scrollX + rect.left}px`;
    // A mousedown on the button would otherwise collapse the page's text selection first,
    // which fires our own `selectionchange` listener and removes this button from the DOM
    // before the click event ever reaches it — so "Explain this" would silently do nothing.
    helpButton.addEventListener("mousedown", (e) => e.preventDefault());
    helpButton.onclick = handleExplainClick;
    document.documentElement.appendChild(helpButton);
  }

  document.addEventListener("selectionchange", () => {
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    if (!text || text.length < 2) {
      hideHelpButton();
      currentSelectionText = null;
      return;
    }
    currentSelectionText = text;
    const anchorNode = selection.anchorNode;
    currentFieldLabel = nearestLabelFor(anchorNode);
    currentOptions = nearestOptionsFor(anchorNode);
    const range = selection.getRangeAt(0);
    showHelpButtonNear(range.getBoundingClientRect());
  });

  // --- Explanation panel ----------------------------------------------------------------------
  let panel = null;
  let lastExplanation = null;
  let lastRequestPayload = null;

  function renderPanel(explanation) {
    if (panel) panel.remove();
    lastExplanation = explanation;
    panel = document.createElement("div");
    panel.className = "asbo-panel";

    const closeBtn = document.createElement("button");
    closeBtn.className = "asbo-panel-close";
    closeBtn.textContent = "✕";
    closeBtn.onclick = () => panel.remove();
    panel.appendChild(closeBtn);

    if (schemeName) {
      const title = document.createElement("div");
      title.className = "asbo-panel-title";
      title.textContent = schemeName;
      panel.appendChild(title);
    }

    const addSection = (label, text, cautionClass) => {
      if (!text) return;
      const l = document.createElement("div");
      l.className = "asbo-panel-label";
      l.textContent = label;
      const p = document.createElement("div");
      p.className = cautionClass ? "asbo-panel-text asbo-panel-caution" : "asbo-panel-text";
      p.textContent = text;
      panel.appendChild(l);
      panel.appendChild(p);
    };

    addSection("What this means", explanation.question_meaning);
    addSection("What to enter", explanation.what_information_is_expected);
    if (explanation.option_explanations?.length) {
      const l = document.createElement("div");
      l.className = "asbo-panel-label";
      l.textContent = "Options";
      panel.appendChild(l);
      for (const o of explanation.option_explanations) {
        const p = document.createElement("div");
        p.className = "asbo-panel-text";
        p.textContent = `${o.option}: ${o.meaning}`;
        panel.appendChild(p);
      }
    }
    addSection("Example", explanation.example);
    addSection("Please note", explanation.important_caution, true);
    if (explanation.needs_clarification && explanation.clarification_question) {
      addSection("We need a bit more context", explanation.clarification_question);
    }

    const controls = document.createElement("div");
    controls.className = "asbo-panel-controls";

    const playBtn = document.createElement("button");
    playBtn.textContent = "🔊 Play";
    playBtn.onclick = () => {
      window.speechSynthesis.cancel();
      const spoken = [explanation.question_meaning, explanation.what_information_is_expected, explanation.important_caution]
        .filter(Boolean)
        .join(". ");
      const utterance = new SpeechSynthesisUtterance(spoken);
      window.speechSynthesis.speak(utterance);
    };
    controls.appendChild(playBtn);

    const stopBtn = document.createElement("button");
    stopBtn.textContent = "⏹ Stop";
    stopBtn.onclick = () => window.speechSynthesis.cancel();
    controls.appendChild(stopBtn);

    const thumbsUp = document.createElement("button");
    thumbsUp.textContent = "👍";
    thumbsUp.title = "This explanation was helpful";
    thumbsUp.onclick = () => sendFeedback(true);
    controls.appendChild(thumbsUp);

    const thumbsDown = document.createElement("button");
    thumbsDown.textContent = "👎";
    thumbsDown.title = "Report incorrect explanation";
    thumbsDown.onclick = () => sendFeedback(false);
    controls.appendChild(thumbsDown);

    panel.appendChild(controls);
    document.documentElement.appendChild(panel);
  }

  async function sendFeedback(isHelpful) {
    if (!lastExplanation || !assistanceToken) return;
    try {
      await fetch(`${API_BASE_URL}/api/assistance/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${assistanceToken}`,
          "X-Assistance-Origin": origin,
        },
        body: JSON.stringify({
          selected_text: lastRequestPayload?.selected_text,
          field_label: lastRequestPayload?.field_label,
          explanation_given: lastExplanation.question_meaning,
          is_helpful: isHelpful,
        }),
      });
    } catch {
      // Feedback is best-effort — never surface an error for it.
    }
  }

  async function handleExplainClick() {
    if (!assistanceToken || !currentSelectionText) return;
    hideHelpButton();
    lastRequestPayload = { selected_text: currentSelectionText, field_label: currentFieldLabel, field_options: currentOptions };
    try {
      const res = await fetch(`${API_BASE_URL}/api/assistance/explain-text`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${assistanceToken}`,
          "X-Assistance-Origin": origin,
        },
        body: JSON.stringify({ ...lastRequestPayload, explanation_mode: "text_and_voice" }),
      });
      const data = await res.json();
      renderPanel(data);
    } catch {
      renderPanel({
        question_meaning: "We couldn't reach the assistant right now.",
        what_information_is_expected: "Check your connection and try selecting the text again.",
      });
    }
  }

  // --- Screenshot capture (Section 7 Option B) ------------------------------------------------
  // Only ever captures the region the user explicitly drags a box around — never the full
  // page, never continuously, and always shown back to the user for review/cancel before
  // anything is sent (Section 8's privacy requirements).
  let captureButton = null;
  let selectionOverlay = null;

  function showCaptureButton() {
    captureButton = document.createElement("button");
    captureButton.className = "asbo-capture-button";
    captureButton.textContent = "📷 Capture area";
    captureButton.onclick = startAreaSelection;
    document.documentElement.appendChild(captureButton);
  }

  function startAreaSelection() {
    if (selectionOverlay) return;
    const overlay = document.createElement("div");
    overlay.className = "asbo-selection-overlay";
    const box = document.createElement("div");
    box.className = "asbo-selection-box";
    overlay.appendChild(box);
    document.documentElement.appendChild(overlay);
    selectionOverlay = overlay;

    let startX = 0;
    let startY = 0;
    let dragging = false;

    function onMouseDown(e) {
      dragging = true;
      startX = e.clientX;
      startY = e.clientY;
      box.style.left = `${startX}px`;
      box.style.top = `${startY}px`;
      box.style.width = "0px";
      box.style.height = "0px";
    }
    function onMouseMove(e) {
      if (!dragging) return;
      const x = Math.min(e.clientX, startX);
      const y = Math.min(e.clientY, startY);
      box.style.left = `${x}px`;
      box.style.top = `${y}px`;
      box.style.width = `${Math.abs(e.clientX - startX)}px`;
      box.style.height = `${Math.abs(e.clientY - startY)}px`;
    }
    async function onMouseUp() {
      if (!dragging) return;
      dragging = false;
      const rect = box.getBoundingClientRect();
      overlay.remove();
      selectionOverlay = null;
      if (rect.width < 10 || rect.height < 10) return; // ignore an accidental click/tiny drag
      await captureAndPreview(rect);
    }

    overlay.addEventListener("mousedown", onMouseDown);
    overlay.addEventListener("mousemove", onMouseMove);
    overlay.addEventListener("mouseup", onMouseUp);
  }

  async function captureAndPreview(rect) {
    const response = await chrome.runtime.sendMessage({
      type: "CAPTURE_REGION",
      rect: { x: rect.left, y: rect.top, width: rect.width, height: rect.height },
      devicePixelRatio: window.devicePixelRatio || 1,
    });
    if (!response?.ok) {
      renderPanel({
        question_meaning: "We couldn't capture that area.",
        what_information_is_expected: "Please try again, or select the text directly instead.",
      });
      return;
    }
    showScreenshotPreview(response.croppedBase64);
  }

  function showScreenshotPreview(base64) {
    const overlay = document.createElement("div");
    overlay.className = "asbo-preview-overlay";

    const card = document.createElement("div");
    card.className = "asbo-preview-card";

    const img = document.createElement("img");
    img.className = "asbo-preview-image";
    img.src = `data:image/png;base64,${base64}`;
    card.appendChild(img);

    const warning = document.createElement("p");
    warning.className = "asbo-preview-warning";
    warning.textContent =
      "Check this image before sending — don't include passwords, OTPs, payment details, or ID numbers.";
    card.appendChild(warning);

    const controls = document.createElement("div");
    controls.className = "asbo-panel-controls";

    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "Cancel";
    cancelBtn.onclick = () => overlay.remove();
    controls.appendChild(cancelBtn);

    const sendBtn = document.createElement("button");
    sendBtn.textContent = "Send for explanation";
    sendBtn.onclick = async () => {
      overlay.remove();
      await handleExplainScreenshot(base64);
    };
    controls.appendChild(sendBtn);

    card.appendChild(controls);
    overlay.appendChild(card);
    document.documentElement.appendChild(overlay);
  }

  async function handleExplainScreenshot(base64) {
    if (!assistanceToken) return;
    lastRequestPayload = { selected_text: null, field_label: "(screenshot)" };
    try {
      const res = await fetch(`${API_BASE_URL}/api/assistance/explain-screenshot`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${assistanceToken}`,
          "X-Assistance-Origin": origin,
        },
        body: JSON.stringify({ screenshot_base64: base64, mime_type: "image/png", explanation_mode: "text_and_voice" }),
      });
      const data = await res.json();
      renderPanel(data);
    } catch {
      renderPanel({
        question_meaning: "We couldn't reach the assistant right now.",
        what_information_is_expected: "Check your connection and try again.",
      });
    }
  }

  // --- Boot -------------------------------------------------------------------------------
  injectStyles();
  const validation = await validate();
  if (!validation.valid) {
    showInactiveBanner(validation.reason || "session could not be verified.");
    return;
  }
  assistanceToken = validation.assistance_token;
  schemeName = validation.scheme_name;

  const activeBadge = document.createElement("div");
  activeBadge.className = "asbo-badge";
  activeBadge.textContent = `🛟 ASBO assistance active${schemeName ? ` — ${schemeName}` : ""}`;
  document.documentElement.appendChild(activeBadge);
  setTimeout(() => activeBadge.remove(), 4000);

  showCaptureButton();
})();
