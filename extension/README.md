# ASBO Form Assistant (browser extension)

Explains a confusing scheme application form question — only on a page opened through the
ASBO platform's own verified "Apply Now" link. It does **not** work as a general-purpose
assistant on arbitrary websites.

## Loading it (development)

1. `backend/`: `uvicorn app.main:app --reload` (the extension calls `http://localhost:8000` by
   default — see `content_script.js`'s `API_BASE_URL` constant to point it elsewhere).
2. Chrome/Edge → `chrome://extensions` → enable **Developer mode** → **Load unpacked** → select
   this `extension/` folder.
3. From the ASBO web app, view a scheme with a verified "Apply Now" link and click it. A new
   tab opens at that scheme's real application URL with `?asbo_session=...` appended.

## How activation actually works

1. The ASBO frontend calls `POST /api/assistance/session` when you click "Apply Now" — this
   mints a short-lived `session_id` scoped to that one scheme and the origin of its
   `application_url` (e.g. `https://pmkisan.gov.in`).
2. `background.js` (the service worker) inspects every top-level navigation's URL. If it
   doesn't carry `?asbo_session=...`, **nothing happens at all** — no script is injected, no
   network call is made, no code from this extension runs on that page.
3. Only when the marker is present does `background.js` inject `content_script.js` into that
   one tab, which calls `POST /api/assistance/validate-session` with the `session_id` and the
   page's own origin (read by the browser itself from `window.location.origin` — not something
   page/extension JS can spoof). The backend only issues a working `assistance_token` if that
   origin matches what was stored when the session was created.
4. All further `explain-text`/`feedback` calls carry that token plus an `X-Assistance-Origin`
   header; the backend independently re-checks both on every call (`require_assistance_session`
   in `backend/app/core/auth.py`) — CORS and the extension's own gating are convenience layers,
   not the actual security boundary.

## A known, disclosed trade-off: `host_permissions`

Manifest V3 requires the extension to declare `host_permissions` up front for any page it might
ever inject into. Since a scheme's `application_url` can be *any* government domain — decided
by a curator, not by us in advance — this extension declares broad host permissions
(`http://*/*`, `https://*/*`). **It does not use that permission on any page unless step 2
above finds the session marker.** This is a real, honest limitation to be aware of (some
review processes flag broad host permissions regardless of runtime behavior); the mitigation is
the gating logic in `background.js`, not the manifest.

## What it does and doesn't do

- Activates only via the flow above — never a floating assistant on every page.
- Only reads text the user explicitly selects, and only sends it to the backend when the user
  clicks "Explain this." No continuous page capture, no reading form values the user hasn't
  selected, no screenshots (not implemented in this version — see Limitations).
- Voice playback uses the browser's built-in `speechSynthesis` — no audio is generated
  server-side, and no audio data leaves the browser.
- "👍/👎" sends only the selected text, field label, and the explanation text already shown —
  never a screenshot, never unrelated page content.

## Limitations (honestly, not overclaimed)

- **No screenshot/OCR capture in this version.** The spec's screenshot-crop-and-explain flow
  needs an image pipeline (capture → crop UI → OCR/vision call) that isn't wired up yet — only
  text selection is implemented. Extending `content_script.js`'s capture flow and
  `backend/app/api/assistance.py`'s `/explain-screenshot` endpoint (not yet added) is the
  natural next step.
- **RAG grounding depends on the vector store being built.** `backend/app/rag/` has no
  `data/chroma` index populated in this environment (see plan.md's architecture assessment) —
  until `backend/scripts/ingest_policies.py` is run, `policy_basis` will be empty and
  explanations fall back to general, non-scheme-specific guidance with an honest "could not
  confirm against this scheme's specific policy text" note (by design — never silently upgraded
  to a confident claim).
- **Not published to the Chrome Web Store** — load-unpacked only. A store listing would need
  its own review pass (icons, privacy disclosure, a hosted, non-`localhost` `API_BASE_URL`).
- **Firefox/Safari**: untested. Manifest V3 service workers and `chrome.scripting` are
  Chromium-specific; a Firefox port would need `browser.*` API shims (e.g. via `webextension-polyfill`) and is not attempted here.
- **The mobile counterpart is a separate implementation** (`mobile/src/screens/ApplicationWebViewScreen.js`, an in-app WebView with a JS bridge) — a phone's system browser cannot be
  read/controlled by this extension or the mobile app; that's why the mobile app opens
  applications in its own in-app WebView rather than the external browser.
