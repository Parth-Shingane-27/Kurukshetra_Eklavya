import { useCallback, useEffect, useState } from "react";
import { createGrievance, listGrievancesForCitizen } from "../api/client";
import AppShell from "../components/layout/AppShell";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import StatusBadge from "../components/StatusBadge";
import { getStoredCitizenId } from "../lib/storage";

const CATEGORY_OPTIONS = ["delay", "incorrect information", "technical issue", "general feedback", "other"];

// Feedback/Grievance — an internal platform ticket only, never an official government
// submission (the backend enforces is_official_submission=False; this page never implies
// otherwise).
export default function Grievances() {
  const citizenId = getStoredCitizenId();
  const [category, setCategory] = useState(CATEGORY_OPTIONS[0]);
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const loadTickets = useCallback(() => {
    if (!citizenId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    listGrievancesForCitizen(citizenId)
      .then(setTickets)
      .catch(setLoadError)
      .finally(() => setLoading(false));
  }, [citizenId]);

  useEffect(() => loadTickets(), [loadTickets]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!citizenId || !description.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await createGrievance({ citizenId, category, description: description.trim() });
      setDescription("");
      loadTickets();
    } catch (err) {
      setSubmitError(err);
    } finally {
      setSubmitting(false);
    }
  }

  if (!citizenId) {
    return (
      <AppShell active="grievances" title="Feedback & support tickets">
        <InfoMessage>
          Complete your profile first (via onboarding or the conversational intake) so tickets
          can be linked to it.
        </InfoMessage>
      </AppShell>
    );
  }

  return (
    <AppShell
      active="grievances"
      title="Feedback & support tickets"
      subtitle="Report a problem or ask for help. This creates an internal platform ticket for our team — it is not an official submission to any government department."
    >
      <form className="card" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>
          What's the issue?
          <textarea
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what happened…"
          />
        </label>
        {submitError && <ErrorMessage error={submitError} />}
        <div className="actions">
          <button type="submit" disabled={submitting || !description.trim()}>
            {submitting ? "Submitting…" : "Submit ticket"}
          </button>
        </div>
      </form>

      <div className="card">
        <h2>Your tickets</h2>
        {loading && <LoadingMessage>Loading your tickets…</LoadingMessage>}
        {loadError && <ErrorMessage error={loadError} onRetry={loadTickets} />}
        {!loading && tickets.length === 0 && <InfoMessage>You haven't submitted any tickets yet.</InfoMessage>}
        {tickets.map((t) => (
          <div className="scheme-row" key={t.id}>
            <div>
              <strong>{t.ticket_id}</strong>
              <p className="hint">{t.category}</p>
              <p>{t.description}</p>
              {t.status === "resolved" && t.resolution_note && (
                <p className="hint">Resolution: {t.resolution_note}</p>
              )}
            </div>
            <StatusBadge status={t.status} />
          </div>
        ))}
      </div>
    </AppShell>
  );
}
