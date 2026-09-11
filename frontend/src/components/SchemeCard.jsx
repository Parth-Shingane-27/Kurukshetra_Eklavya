import ApplyLink from "./ApplyLink";
import StatusBadge from "./StatusBadge";

export default function SchemeCard({ scheme, matchStatus, reasons }) {
  const categories = (scheme.category || "")
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean);

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
        {matchStatus && <StatusBadge status={matchStatus} />}
      </div>

      <h3>{scheme.name}</h3>
      {scheme.issuing_authority && <p className="scheme-card-authority">{scheme.issuing_authority}</p>}
      {scheme.description && <p className="scheme-card-desc">{scheme.description}</p>}

      <div className="scheme-card-benefit">
        ₹{scheme.benefit_value_estimate.toLocaleString()}
        <span> · {scheme.benefit_type.replaceAll("_", " ")}</span>
      </div>

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
                <li key={i}>{r.message}</li>
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
    </article>
  );
}
