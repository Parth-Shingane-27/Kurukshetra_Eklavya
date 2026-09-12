import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAllGrievances, resolveGrievance } from "../api/client";
import { getUser, isLoggedIn, subscribe } from "../auth/session";
import AppShell from "../components/layout/AppShell";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import StatusBadge from "../components/StatusBadge";

export default function AdminGrievances() {
  const [sessionUser, setSessionUser] = useState(getUser());
  const isAdmin = isLoggedIn() && sessionUser?.role === "admin";

  const [statusFilter, setStatusFilter] = useState("open");
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [resolvingId, setResolvingId] = useState(null);
  const [resolutionNote, setResolutionNote] = useState("");

  useEffect(() => subscribe(() => setSessionUser(getUser())), []);

  const loadTickets = useCallback(() => {
    setLoading(true);
    listAllGrievances(statusFilter || undefined)
      .then(setTickets)
      .catch(setLoadError)
      .finally(() => setLoading(false));
  }, [statusFilter]);

  useEffect(() => loadTickets(), [loadTickets]);

  async function handleResolve(id) {
    if (!resolutionNote.trim()) return;
    setActionError(null);
    try {
      await resolveGrievance(id, resolutionNote.trim());
      setResolvingId(null);
      setResolutionNote("");
      loadTickets();
    } catch (err) {
      setActionError(err);
    }
  }

  return (
    <AppShell
      variant="admin"
      active="admin-grievances"
      title="Grievance review queue"
      subtitle="Internal support tickets submitted by citizens — not official government complaints."
    >
      <div className="card">
        {isAdmin ? (
          <InfoMessage>Logged in as {sessionUser.email} (admin).</InfoMessage>
        ) : (
          <InfoMessage>
            <Link to="/login">Log in</Link> with an admin account to resolve tickets.
          </InfoMessage>
        )}
      </div>

      <div className="card">
        <div className="scheme-row">
          <h2>Tickets</h2>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
            <option value="">All</option>
          </select>
        </div>

        {loading && <LoadingMessage>Loading tickets…</LoadingMessage>}
        {loadError && <ErrorMessage error={loadError} onRetry={loadTickets} />}
        {actionError && <ErrorMessage error={actionError} />}
        {!loading && tickets.length === 0 && <InfoMessage>No tickets in this status.</InfoMessage>}

        {tickets.map((t) => (
          <div className="card catalog-item" key={t.id}>
            <div className="scheme-row">
              <div>
                <strong>{t.ticket_id}</strong>
                <p className="hint">
                  {t.category} · citizen: {t.citizen_id} {t.department && `· ${t.department}`}
                </p>
                <p>{t.description}</p>
              </div>
              <StatusBadge status={t.status} />
            </div>

            {t.status === "resolved" && t.resolution_note && <p className="hint">Resolution: {t.resolution_note}</p>}

            {isAdmin && t.status === "open" && (
              <div className="actions">
                {resolvingId === t.id ? (
                  <>
                    <input
                      type="text"
                      placeholder="Resolution note"
                      value={resolutionNote}
                      onChange={(e) => setResolutionNote(e.target.value)}
                    />
                    <button type="button" onClick={() => handleResolve(t.id)} disabled={!resolutionNote.trim()}>
                      Confirm resolve
                    </button>
                  </>
                ) : (
                  <button type="button" className="secondary" onClick={() => setResolvingId(t.id)}>
                    Resolve
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
