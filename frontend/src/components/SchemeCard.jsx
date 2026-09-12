import { useState } from "react";
import { saveScheme, unsaveScheme } from "../api/client";
import ApplyLink from "./ApplyLink";
import DeadlineBadge from "./DeadlineBadge";
import StatusBadge from "./StatusBadge";
import { humanizeReason } from "../lib/reasonText";

export default function SchemeCard({ scheme, matchStatus, reasons, citizenId, citation, initialSaved = false, onSavedChange }) {
  const categories = (scheme.category || "")
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean);

  const [saved, setSaved] = useState(initialSaved);
  const [savingBusy, setSavingBusy] = useState(false);

  async function toggleSave() {
    if (!citizenId || savingBusy) return;
    setSavingBusy(true);
    try {
      if (saved) {
        await unsaveScheme(citizenId, scheme.id);
        setSaved(false);
        onSavedChange?.(scheme.id, false);
      } else {
        await saveScheme(citizenId, scheme.id);
        setSaved(true);
        onSavedChange?.(scheme.id, true);
      }
    } catch {
      /* leave saved state unchanged on failure — citizen can retry */
    } finally {
      setSavingBusy(false);
    }
  }

  return (
    <article className="scheme-card">
      <div className="scheme-card-top">
        <div className="scheme-card-tags">
          {categories.map((c) => (
            <span key={c} className="chip chip-tag">
              {c}
            </span>
          ))}
        </div>
        <div className="scheme-card-top-right">
          {matchStatus && <StatusBadge status={matchStatus} />}
          {citizenId && (
            <button
              type="button"
              className="scheme-card-save"
              onClick={toggleSave}
              disabled={savingBusy}
              aria-label={saved ? "Remove from saved schemes" : "Save this scheme"}
              title={saved ? "Remove from saved schemes" : "Save this scheme"}
            >
              {saved ? "★" : "☆"}
            </button>
          )}
        </div>
      </div>

      <h3>{scheme.name}</h3>
      {scheme.issuing_authority && <p className="scheme-card-authority">{scheme.issuing_authority}</p>}
      {scheme.description && <p className="scheme-card-desc">{scheme.description}</p>}

      <div className="scheme-card-benefit">
        ₹{scheme.benefit_value_estimate.toLocaleString()}
        <span> · {scheme.benefit_type.replaceAll("_", " ")}</span>
      </div>

      <DeadlineBadge schemeId={scheme.id} />

      {matchStatus === "eligible" && (
        <ApplyLink
          url={scheme.links?.application_url}
          status={scheme.links?.application_link_status}
          moreInfoUrl={scheme.links?.official_scheme_url}
          schemeId={scheme.id}
        />
      )}

      <details className="scheme-card-details">
        <summary>Requirements &amp; documents</summary>
        {reasons && reasons.length > 0 && (
          <div className="reasons">
            <ul>
              {reasons.map((r, i) => (
                <li key={i}>{humanizeReason(r)}</li>
              ))}
            </ul>
          </div>
        )}
        {scheme.document_requirements.length > 0 && (
          <>
            <p className="hint">Documents needed:</p>
            <ul>
              {scheme.document_requirements.map((d) => (
                <li key={d.document_type}>
                  {d.document_type}
                  {!d.is_mandatory && " (optional)"}
                </li>
              ))}
            </ul>
          </>
        )}
      </details>

      {citation?.evidence?.length > 0 && (
        <details className="scheme-card-details">
          <summary>Curated from policy sources</summary>
          <ul className="reasons">
            {citation.evidence.map((e, i) => (
              <li key={i}>
                {e.content}
                {e.source_url && (
                  <>
                    {" "}
                    <a href={e.source_url} target="_blank" rel="noreferrer">
                      Source
                    </a>
                  </>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}
