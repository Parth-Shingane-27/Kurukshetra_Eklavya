import { useState } from "react";
import { createAssistanceSession } from "../api/client";

const STATUS_COPY = {
  verified: {
    label: "Apply Now ↗",
    note: null,
    tone: "success",
  },
  unverified: {
    label: "Apply Now ↗",
    note: "This link has not been independently verified — check the web address carefully before entering any personal details.",
    tone: "warning",
  },
  not_available: {
    label: null,
    note: "Online application is not available for this scheme. Please follow the official offline application process.",
    tone: "info",
  },
  state_specific: {
    label: null,
    note: "The application process varies by state/department — check with your local office for the correct portal.",
    tone: "info",
  },
};

// Statuses the assistance browser extension/mobile toggle can actually attach to — matches
// the backend's own _ASSISTABLE_STATUSES (app/modules/assistance/service.py). There is
// nothing to assist with when there's no real (even if unverified) destination.
const ASSISTABLE_STATUSES = new Set(["verified", "unverified"]);

// Renders a scheme's application destination honestly: a clear "Apply Now"-style link only
// when the destination has been verified (BR-019); an explicit warning banner for an
// unverified link; and a plain-text explanation (no link at all) when no online application
// exists or it depends on the citizen's state — never a fabricated/best-guess URL.
//
// When `schemeId` is supplied, clicking the link first mints a short-lived assistance session
// (see app/api/assistance.py) and appends it to the URL as `?asbo_session=...` — this is what
// the browser extension reads to decide whether to activate on that page at all (Section 6:
// "the extension must not activate as a generic assistant on arbitrary websites"). If session
// creation fails for any reason, the citizen can still apply normally — assistance is strictly
// additive and must never block the actual application flow.
export default function ApplyLink({ url, status, moreInfoUrl, schemeId }) {
  const copy = STATUS_COPY[status] || STATUS_COPY.unverified;
  const [opening, setOpening] = useState(false);

  async function handleClick(e) {
    if (!schemeId || !ASSISTABLE_STATUSES.has(status)) return; // plain link, no session needed
    e.preventDefault();
    setOpening(true);
    try {
      const session = await createAssistanceSession(schemeId);
      const separator = url.includes("?") ? "&" : "?";
      window.open(`${url}${separator}asbo_session=${encodeURIComponent(session.session_id)}`, "_blank", "noopener");
    } catch {
      window.open(url, "_blank", "noopener");
    } finally {
      setOpening(false);
    }
  }

  if (!url) {
    if (!copy.note) return null;
    return (
      <div className={`apply-link-block apply-link-${copy.tone}`}>
        <p className="apply-note">{copy.note}</p>
        {moreInfoUrl && (
          <a href={moreInfoUrl} target="_blank" rel="noreferrer">
            More information ↗
          </a>
        )}
      </div>
    );
  }

  return (
    <div className={`apply-link-block apply-link-${copy.tone}`}>
      <a href={url} target="_blank" rel="noreferrer" className="apply-link apply-button" onClick={handleClick}>
        {opening ? "Opening…" : copy.label}
      </a>
      {copy.note && <p className="apply-note">{copy.note}</p>}
      {ASSISTABLE_STATUSES.has(status) && schemeId && (
        <p className="apply-note apply-assist-hint">
          If you have our companion browser extension installed, form help will be available on this page.
        </p>
      )}
    </div>
  );
}
