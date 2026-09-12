import { useState } from "react";
import { createSchemeReport } from "../api/client";
import { getStoredCitizenId } from "../lib/storage";
import { ErrorMessage, InfoMessage } from "./StateMessage";

const REASONS = [
  "Outdated benefit amount",
  "Wrong eligibility criteria",
  "Broken/incorrect application link",
  "Guide is inaccurate",
  "Other",
];

// Section 21 (Data Quality) — lets any citizen (anonymous or not) flag a scheme's information
// as wrong, feeding an admin review queue. Distinct from FR-015's RAG candidate queue: this is
// a raw citizen claim, never auto-applied to the scheme record.
export default function ReportSchemeControl({ schemeId }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState(REASONS[0]);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createSchemeReport({ schemeId, reason, comment, citizenId: getStoredCitizenId() });
      setSubmitted(true);
      setOpen(false);
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return <InfoMessage>Thanks — this has been sent to our team for review.</InfoMessage>;
  }

  if (!open) {
    return (
      <button type="button" className="ghost small" onClick={() => setOpen(true)}>
        ⚑ Report incorrect info
      </button>
    );
  }

  return (
    <form className="report-scheme-form" onSubmit={handleSubmit}>
      <label>
        What's wrong?
        <select value={reason} onChange={(e) => setReason(e.target.value)}>
          {REASONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </label>
      <label>
        Details (optional)
        <input type="text" value={comment} onChange={(e) => setComment(e.target.value)} />
      </label>
      {error && <ErrorMessage error={error} />}
      <div className="actions">
        <button type="submit" disabled={submitting}>
          {submitting ? "Sending…" : "Submit report"}
        </button>
        <button type="button" className="ghost" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </form>
  );
}
