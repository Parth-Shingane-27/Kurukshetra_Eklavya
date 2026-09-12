import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSchemeReports, resolveSchemeReport } from "../api/client";
import { getUser, isLoggedIn, subscribe } from "../auth/session";
import AppShell from "../components/layout/AppShell";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import StatusBadge from "../components/StatusBadge";

export default function AdminSchemeReports() {
  const [sessionUser, setSessionUser] = useState(getUser());
  const isAdmin = isLoggedIn() && sessionUser?.role === "admin";

  const [statusFilter, setStatusFilter] = useState("open");
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [resolvingId, setResolvingId] = useState(null);
  const [adminNotes, setAdminNotes] = useState("");

  useEffect(() => subscribe(() => setSessionUser(getUser())), []);

  const loadReports = useCallback(() => {
    setLoading(true);
    listSchemeReports(statusFilter || undefined)
      .then(setReports)
      .catch(setLoadError)
      .finally(() => setLoading(false));
  }, [statusFilter]);

  useEffect(() => loadReports(), [loadReports]);

  async function handleResolve(id, status) {
    setActionError(null);
    try {
      await resolveSchemeReport(id, status, adminNotes.trim() || undefined);
      setResolvingId(null);
      setAdminNotes("");
      loadReports();
    } catch (err) {
      setActionError(err);
    }
  }

  return (
    <AppShell
      variant="admin"
      active="admin-reports"
      title="Scheme data-quality reports"
      subtitle="Citizen-flagged inaccuracies — a raw claim to look into, never auto-applied to the scheme record."
    >
      <div className="card">
        {isAdmin ? (
          <InfoMessage>Logged in as {sessionUser.email} (admin).</InfoMessage>
        ) : (
          <InfoMessage>
            <Link to="/login">Log in</Link> with an admin account to resolve reports.
          </InfoMessage>
        )}
      </div>

      <div className="card">
        <div className="scheme-row">
          <h2>Reports</h2>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="open">Open</option>
            <option value="addressed">Addressed</option>
            <option value="dismissed">Dismissed</option>
            <option value="">All</option>
          </select>
        </div>

        {loading && <LoadingMessage>Loading reports…</LoadingMessage>}
        {loadError && <ErrorMessage error={loadError} onRetry={loadReports} />}
        {actionError && <ErrorMessage error={actionError} />}
        {!loading && reports.length === 0 && <InfoMessage>No reports in this status.</InfoMessage>}

        {reports.map((r) => (
          <div className="card catalog-item" key={r.id}>
            <div className="scheme-row">
              <div>
                <strong>{r.scheme_name}</strong>
                <p className="hint">{r.reason}</p>
                {r.comment && <p>{r.comment}</p>}
              </div>
              <StatusBadge status={r.status === "addressed" ? "resolved" : r.status} />
            </div>

            {r.admin_notes && <p className="hint">Notes: {r.admin_notes}</p>}

            {isAdmin && r.status === "open" && (
              <div className="actions">
                {resolvingId === r.id ? (
                  <>
                    <input
                      type="text"
                      placeholder="Admin notes (optional)"
                      value={adminNotes}
                      onChange={(e) => setAdminNotes(e.target.value)}
                    />
                    <button type="button" onClick={() => handleResolve(r.id, "addressed")}>
                      Mark addressed
                    </button>
                    <button type="button" className="secondary" onClick={() => handleResolve(r.id, "dismissed")}>
                      Dismiss
                    </button>
                  </>
                ) : (
                  <button type="button" className="secondary" onClick={() => setResolvingId(r.id)}>
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
