import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listGrievancesForCitizen, listNotifications, listSavedSchemes } from "../api/client";
import AppShell from "../components/layout/AppShell";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { getStoredCitizenId } from "../lib/storage";

// Activity & History — a single timeline composed from data that already exists elsewhere
// (notifications, grievance tickets, saved schemes) rather than a new, duplicated log. The
// full step-by-step reasoning trace already has its own dedicated page (Trace.jsx); this page
// links to it instead of re-showing it inline.
export default function Activity() {
  const navigate = useNavigate();
  const citizenId = getStoredCitizenId();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [events, setEvents] = useState([]);

  useEffect(() => {
    if (!citizenId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([
      listNotifications(citizenId).catch(() => []),
      listGrievancesForCitizen(citizenId).catch(() => []),
      listSavedSchemes(citizenId).catch(() => []),
    ])
      .then(([notifications, grievances, saved]) => {
        const timeline = [
          ...notifications.map((n) => ({
            timestamp: n.created_at,
            label: n.message,
            kind: n.type.startsWith("grievance") ? "Support ticket" : "Reminder",
          })),
          ...grievances.map((g) => ({
            timestamp: g.created_at,
            label: `Submitted support ticket ${g.ticket_id} (${g.category})`,
            kind: "Support ticket",
          })),
          ...saved.map((s) => ({
            timestamp: s.saved_at,
            label: `Saved scheme: ${s.scheme_name}`,
            kind: "Saved scheme",
          })),
        ];
        timeline.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        setEvents(timeline);
      })
      .catch(setError)
      .finally(() => setLoading(false));
  }, [citizenId]);

  if (!citizenId) {
    return (
      <AppShell active="activity" title="Activity">
        <InfoMessage>Complete your profile first to see your activity.</InfoMessage>
      </AppShell>
    );
  }

  return (
    <AppShell
      active="activity"
      title="Your activity"
      subtitle="A history of what's happened on your account."
      meta={
        <button type="button" className="link-button" onClick={() => navigate(`/citizens/${citizenId}/trace`)}>
          View the full step-by-step reasoning trace →
        </button>
      }
    >
      {loading && <LoadingMessage>Loading your activity…</LoadingMessage>}
      {error && <ErrorMessage error={error} />}
      {!loading && events.length === 0 && <InfoMessage>Nothing to show yet.</InfoMessage>}

      <div className="card">
        {events.map((e, i) => (
          <div className="scheme-row" key={i}>
            <div>
              <span className="chip chip-tag">{e.kind}</span>
              <p>{e.label}</p>
            </div>
            <span className="hint">{new Date(e.timestamp).toLocaleString()}</span>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
