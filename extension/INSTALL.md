# Installing ASBO Form Assistant — free, no store account needed

This installs the extension directly in your browser without going through the Chrome Web
Store or Firefox Add-ons site — completely free, no developer account, no review wait. This is
"developer mode" / "temporary add-on" loading, the same thing web developers use while
building an extension.

A ready-to-use package is already built at `extension/dist/asbo-form-assistant.zip`. To rebuild
it after any change to the extension's source files:

```bash
cd extension
rm -f dist/asbo-form-assistant.zip
zip -r dist/asbo-form-assistant.zip manifest.json background.js content_script.js injected_styles.css popup.html popup.js icons
```

## Chrome / Edge / Brave (any Chromium browser) — persists across restarts

1. Unzip `extension/dist/asbo-form-assistant.zip` into its own folder anywhere on your computer
   (e.g. `Documents/asbo-extension/`).
2. Go to `chrome://extensions` (or `edge://extensions`).
3. Turn on **Developer mode** (top-right toggle).
4. Click **Load unpacked** and select the folder you unzipped into.
5. Done — the extension icon appears in your toolbar and stays installed until you remove it,
   even after restarting the browser. Chrome will occasionally show a "disable developer mode
   extensions" nag banner; just dismiss it — this is expected for unpacked extensions and
   doesn't affect functionality.

To update later: replace the folder's contents with a newer build, then click the refresh icon
on the extension's card at `chrome://extensions`.

## Firefox — quick way (until you restart Firefox)

1. Go to `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on…**.
3. Select the `manifest.json` file inside the unzipped folder (not the zip itself, not the
   folder — the file).
4. It installs immediately. **Limitation:** Firefox removes temporary add-ons when you close
   the browser — you'll need to repeat this each time you restart Firefox. This is a Firefox
   policy for unsigned extensions, not something this extension can work around.

## Firefox — persists across restarts, still free, no AMO listing needed

Mozilla will still digitally sign an extension for free even if you don't publish it publicly:

```bash
cd extension
npx web-ext sign --source-dir . --api-key=<your-AMO-API-key> --api-secret=<your-AMO-API-secret> --channel unlisted
```

This needs a free AMO (addons.mozilla.org) account and an API key/secret from
https://addons.mozilla.org/developers/addon/api/key/ — no paid fee, no public listing, no
review wait for "unlisted" — it just needs Mozilla's automated signing step, which is instant
to a few minutes. The signed `.xpi` file it produces can then be installed permanently via
`about:addons` → gear icon → **Install Add-on From File…**.

## What you get either way

Same extension, same code, same functionality as a Chrome Web Store / AMO listing would give
you — the only difference is discoverability (nobody can find it by searching the store) and,
for Firefox's quick method, that it needs reloading after each browser restart. For sharing
with teammates or judges during a hackathon, the zip + "Load unpacked" method above is the
fastest path and needs nothing from anyone but a browser.
