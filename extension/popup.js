const statusEl = document.getElementById("status");

chrome.runtime.sendMessage({ type: "GET_ACTIVE_TAB_SESSION_MARKER" }, (response) => {
  if (response?.sessionId) {
    statusEl.textContent = "Active on this tab — a scheme application session was detected.";
    statusEl.className = "status status-active";
  } else {
    statusEl.textContent = "Inactive — open a scheme's verified application link from ASBO to enable assistance.";
    statusEl.className = "status status-inactive";
  }
});
