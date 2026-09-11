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
  return false;
});
