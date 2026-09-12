# Store listing content (Chrome Web Store + Firefox AMO)

Everything below is drafted and ready to paste. The only things you still have to do yourself
are the account/payment/review steps that need your own identity (see the checklists at the
bottom of each section).

## Before you submit (already done)

- [x] `manifest.json` has `icons`/`action.default_icon` at 16/32/48/128px (`extension/icons/`)
- [x] `manifest.json` has a `browser_specific_settings.gecko` block (id, `strict_min_version`,
  `data_collection_permissions`) so it's accepted by Firefox's AMO validator
- [x] `background.scripts` added alongside `background.service_worker` so the same manifest
  works as a Firefox-compatible fallback (Chrome/Edge use the service worker; Firefox uses the
  scripts array — both point at the same `background.js`)
- [x] Verified with Mozilla's own linter: `npx web-ext lint --source-dir extension/` → **0
  errors** (2 harmless informational warnings: Firefox ignoring the Chrome-only
  `service_worker` key by design, and a Firefox-for-Android version note that doesn't apply
  since this extension isn't targeting mobile Firefox)
- [x] Re-verified the extension still loads cleanly in Chrome after all manifest changes
  (service worker registers, zero errors) via a live Playwright check

## Packaging (do this once you're ready to submit)

From the repo root:

```bash
cd extension
# Chrome Web Store wants a .zip of the folder CONTENTS, not the folder itself
zip -r ../asbo-form-assistant-chrome.zip . -x "*.md"
```

For Firefox, `web-ext build` produces a signable package with the right structure automatically:

```bash
cd extension
npx web-ext build --source-dir . --artifacts-dir ../web-ext-artifacts
```

## Chrome Web Store listing

- **Store display name:** ASBO Form Assistant
- **Summary (132 char max):**
  "Explains confusing government scheme application questions — only on pages opened through ASBO's own verified Apply link."
- **Description (long):**

  > ASBO Form Assistant helps citizens understand confusing questions on government scheme
  > application forms. It activates only when you reach an application page through ASBO's own
  > verified "Apply Now" link — never as a general-purpose assistant on other sites.
  >
  > How it works: select any confusing text on the form, or draw a box around a section to
  > capture it as a screenshot, and the assistant explains what's being asked in plain language
  > — grounded in the scheme's own official policy text, never guessing at eligibility. It
  > never fills in or submits the form for you, and never captures anything unless you
  > explicitly click to ask for help.
  >
  > Requires the free ASBO web app (see the GitHub repository for setup) — this extension is
  > the companion browser assistant for that platform.

- **Category:** Productivity (or Social Impact / Government if your listing flow offers it)
- **Language:** English
- **Screenshots (1280×800 or 640×400, at least 1 required):** [YOUR INPUT NEEDED — capture
  from a live demo: (1) the "Explain this" button after selecting form text, (2) the
  explanation popup, (3) the screenshot-capture flow with its preview warning]
- **Small promo tile (440×280, optional but recommended):** [YOUR INPUT NEEDED]
- **Privacy practices (required as of Chrome's Manifest V3 policy):**
  - *Single purpose description:* "Explains government scheme application form questions to
    the citizen, only on pages reached through the ASBO platform's own verified application
    link."
  - *Permission justifications:*
    - `webNavigation` — "Used only to detect when a tab navigates to a URL carrying our own
      session marker (`?asbo_session=...`), so the extension can decide whether to activate on
      that specific tab. No other navigation data is read or stored."
    - `scripting` — "Injects the assistant's UI only into the one tab that just navigated to a
      URL carrying our session marker — never on any other page."
    - `storage` — "Stores the current session's short-lived assistance token locally so
      repeated calls on the same page don't need to re-authenticate."
    - `host_permissions: <all_urls>` — "A scheme's real government application URL can be any
      domain, decided by a human curator at data-entry time, not known in advance by this
      extension. `<all_urls>` is specifically required by `chrome.tabs.captureVisibleTab` for
      the optional screenshot-capture feature (the narrower `http://*/*` + `https://*/*` pair
      is not accepted by that one API). The extension does not act on this permission unless
      the session-marker check above passes first — see `background.js`'s gating logic."
  - *Data usage disclosure:* "This extension transmits only what the user explicitly selects
    (highlighted text, or a screenshot region they drew and confirmed) plus the form field's
    own label, to our backend for a grounded explanation. It does not collect browsing history,
    passwords, financial information, or any data not explicitly selected by the user for this
    one purpose. See the linked privacy policy."
  - *Privacy policy URL:* [YOUR INPUT NEEDED — host a short privacy-policy page; can be a
    single page in the ASBO web app, e.g. `/privacy`, or a page in this GitHub repo rendered via
    GitHub Pages]

### What only you can do (Chrome)

- [ ] Sign up as a Chrome Web Store developer (one-time $5 fee):
  https://chrome.google.com/webstore/devconsole
- [ ] Upload the zipped package, paste the listing content above, add screenshots
- [ ] Provide/host a privacy policy URL and paste it into the listing
- [ ] Submit for review (review time varies, commonly a few days to ~2 weeks; broad host
  permissions like `<all_urls>` sometimes trigger closer manual review — the justification
  text above is written specifically to address that)

## Firefox (addons.mozilla.org) listing

- **Name / Summary / Description:** same copy as the Chrome listing above.
- **Categories:** Productivity, or Privacy & Security.
- **License:** [YOUR INPUT NEEDED — pick one, e.g. MIT, matching whatever license you choose
  for the repository]

### What only you can do (Firefox)

- [ ] Create a free Firefox account and go to https://addons.mozilla.org/developers/
- [ ] Submit the package built by `web-ext build` above (or let AMO build it from source)
- [ ] AMO's own automated validator will run the same checks `web-ext lint` already caught
  ahead of time — expect it to pass cleanly given the fixes already made
- [ ] Choose "Listed" (public, goes through human review) or "Unlisted" (self-distributed,
  still signed by Mozilla but not in the public directory — faster if you just want a signed
  build for the hackathon demo)

## Safari — genuinely needs a Mac + Xcode, no way around it

Safari Web Extensions are packaged as a native macOS/iOS app wrapper, built through Xcode's
"Convert Web Extension" tool, then submitted via App Store Connect. This cannot be done from a
Windows machine or from this session — it requires:

- [ ] A Mac with Xcode installed
- [ ] An Apple Developer Program membership ($99/year)
- [ ] Running `xcrun safari-web-extension-converter extension/` on that Mac, then building and
  submitting the generated Xcode project through App Store Connect

If a Safari port isn't essential for your hackathon deadline, it's reasonable to ship Chrome +
Firefox now and defer Safari.
