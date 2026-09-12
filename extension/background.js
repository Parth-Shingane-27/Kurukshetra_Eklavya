// Background service worker — the ONLY place that decides whether the content script ever
// runs on a page at all (Section 6: "must not activate as a generic assistant on arbitrary
// websites"). Manifest V3 requires broad host_permissions to be *able* to inject into an
// arbitrary government domain we can't enumerate in advance (every scheme has its own
// application portal), but that permission is never exercised unless the page's own URL
// carries the `asbo_session` marker our platform generated at "Apply Now" time — every other
// page is left completely untouched, no script is ever injected into it.

const SESSION_PARAM = "asbo_session";

function extractSessionId(url) {
  try {
    const parsed = new URL(url);
    return parsed.searchParams.get(SESSION_PARAM);
  } catch {
    return null;
  }
}

chrome.webNavigation.onCommitted.addListener(async (details) => {
  if (details.frameId !== 0) return; // top-level frame only — never a nested iframe/ad
  const sessionId = extractSessionId(details.url);
  if (!sessionId) return; // no marker => this page is untouched, full stop

  await chrome.scripting.executeScript({
    target: { tabId: details.tabId },
    files: ["content_script.js"],
  });
});

// Lets the popup ask "is assistance active on the current tab?" without re-deriving the URL
// parsing logic in two places.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "GET_TAB_SESSION_MARKER" && sender.tab?.url) {
    sendResponse({ sessionId: extractSessionId(sender.tab.url) });
    return true;
  }
  if (message?.type === "GET_ACTIVE_TAB_SESSION_MARKER") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const url = tabs[0]?.url;
      sendResponse({ sessionId: url ? extractSessionId(url) : null });
    });
    return true; // keep the message channel open for the async chrome.tabs.query callback
  }
  if (message?.type === "CAPTURE_REGION" && sender.tab) {
    (async () => {
      try {
        // Captures only the current viewport (never the full scrollable page — there is no
        // API for that, and it wouldn't match Section 8's "capture only the selected region"
        // requirement anyway), then crops to exactly the rectangle the user drew.
        const dataUrl = await chrome.tabs.captureVisibleTab(sender.tab.windowId, { format: "png" });
        const croppedBase64 = await cropDataUrl(dataUrl, message.rect, message.devicePixelRatio || 1);
        sendResponse({ ok: true, croppedBase64 });
      } catch (err) {
        sendResponse({ ok: false, error: String(err) });
      }
    })();
    return true;
  }
  return false;
});

async function cropDataUrl(dataUrl, rect, dpr) {
  const response = await fetch(dataUrl);
  const blob = await response.blob();
  const bitmap = await createImageBitmap(blob);

  const sx = Math.max(0, Math.round(rect.x * dpr));
  const sy = Math.max(0, Math.round(rect.y * dpr));
  const sw = Math.max(1, Math.round(rect.width * dpr));
  const sh = Math.max(1, Math.round(rect.height * dpr));

  const canvas = new OffscreenCanvas(sw, sh);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(bitmap, sx, sy, sw, sh, 0, 0, sw, sh);
  const croppedBlob = await canvas.convertToBlob({ type: "image/png" });
  const buffer = await croppedBlob.arrayBuffer();

  let binary = "";
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}
