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
})();
