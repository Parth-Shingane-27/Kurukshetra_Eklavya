# ASBO Form Assistant (browser extension)

Explains a confusing scheme application form question — only on a page opened through the
ASBO platform's own verified "Apply Now" link. It does **not** work as a general-purpose
assistant on arbitrary websites.

## Loading it (development, or just to use it — free, no store account needed)

1. `backend/`: `uvicorn app.main:app --reload` (the extension calls `http://localhost:8000` by
   default — see `content_script.js`'s `API_BASE_URL` constant to point it elsewhere).
2. Chrome/Edge → `chrome://extensions` → enable **Developer mode** → **Load unpacked** → select
   this `extension/` folder (or the pre-built `extension/dist/asbo-form-assistant.zip`,
   unzipped — see `INSTALL.md` for the full free-install walkthrough, including a Firefox path).
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
by a curator, not by us in advance — this extension declares the literal `<all_urls>` host
permission (required specifically for `chrome.tabs.captureVisibleTab` in the screenshot flow
below — the equivalent `http://*/*` + `https://*/*` pair is accepted for script injection but
not for that one API). **It does not use that permission on any page unless step 2 above finds
the session marker.** This is a real, honest trade-off to be aware of (some review processes
flag broad host permissions regardless of runtime behavior); the mitigation is the gating logic
in `background.js`, not the manifest.

## What it does and doesn't do

- Activates only via the flow above — never a floating assistant on every page.
- Two ways to ask for help, both explicit and user-initiated — nothing is ever captured or sent
  automatically:
  - **Select text** on the form, then click "🛟 Explain this."
  - **Click "📷 Capture area,"** drag a box around just the relevant part of the form (only that
    region is captured — `chrome.tabs.captureVisibleTab` + an in-`background.js` crop, never the
    full page), review a **preview** with a "don't include passwords/OTPs/payment details/ID
    numbers" warning, then explicitly click "Send for explanation" (or "Cancel" — nothing is
    sent, and the image is discarded either way once the request completes; it's never written
    to disk or logged, client or server side).
- A screenshot is transcribed by the same Gemini model already used for explanations (no
  separate OCR dependency), then flows through the identical retrieval/explanation/eligibility-
  caution pipeline as a text selection — see `app/graph/form_assistance_workflow.py`'s
  `extract_form_context_node`.
- Voice playback uses the browser's built-in `speechSynthesis` — no audio is generated
  server-side, and no audio data leaves the browser.
- "👍/👎" sends only the selected text (or a "(screenshot)" marker), field label, and the
  explanation text already shown — never the screenshot image itself, never unrelated page
  content.

## Limitations (honestly, not overclaimed)

- **RAG grounding depends on the vector store being built.** `backend/app/rag/` has no
  `data/chroma` index populated in this environment (see plan.md's architecture assessment) —
  until `backend/scripts/ingest_policies.py` is run, `policy_basis` will be empty and
  explanations fall back to general, non-scheme-specific guidance with an honest "could not
  confirm against this scheme's specific policy text" note (by design — never silently upgraded
  to a confident claim).
- **Not yet published to the Chrome Web Store or addons.mozilla.org** — load-unpacked only.
  Everything short of the actual account signup/payment/review is now prepared: icons at
  16/32/48/128px, a `browser_specific_settings.gecko` manifest block, and drafted listing copy
  with permission justifications — see `STORE_LISTING.md` for the exact remaining steps and
  what only a human with store-developer accounts can do. A hosted, non-`localhost`
  `API_BASE_URL` is still required before a real public listing goes live (`content_script.js`
  currently points at `http://localhost:8000`).
- **Firefox**: the manifest now validates cleanly against Mozilla's own `web-ext lint` (0
  errors) — `background.scripts` is declared alongside `background.service_worker` as a
  Firefox-compatible fallback, since both point at the same `background.js`, which is written
  entirely against the `chrome.*` namespace (Firefox aliases `chrome.*` to `browser.*` for MV3
  compatibility, so no `webextension-polyfill` was needed for the APIs this extension actually
  uses). **Not runtime-tested in an actual Firefox instance** — Playwright cannot load arbitrary
  extensions into its Firefox build, so this is a static/lint-level compatibility pass only, not
  a live-verified one; `chrome.tabs.captureVisibleTab` and `OffscreenCanvas` (used by the
  screenshot-capture flow) should work under Firefox's `chrome.*` alias but haven't been
  clicked-through by a human in real Firefox yet.
- **Safari**: still needs a Mac + Xcode + Apple Developer account to convert and submit — see
  `STORE_LISTING.md`'s Safari section. Not attempted; there is no way to do this from this
  environment.
- **The mobile counterpart is a separate implementation** (`mobile/src/screens/ApplicationWebViewScreen.js`, an in-app WebView with a JS bridge) — a phone's system browser cannot be
  read/controlled by this extension or the mobile app; that's why the mobile app opens
  applications in its own in-app WebView rather than the external browser.
