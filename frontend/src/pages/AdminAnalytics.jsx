import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAnalytics } from "../api/client";
import { getUser, isLoggedIn, subscribe } from "../auth/session";
import AppShell from "../components/layout/AppShell";
import { ErrorMessage, LoadingMessage } from "../components/StateMessage";

function StatCard({ label, value }) {
  return (
    <div className="stat-card">
      <div className="stat-card-value">{value}</div>
      <div className="stat-card-label">{label}</div>
    </div>
  );
}

export default function AdminAnalytics() {
  const [sessionUser, setSessionUser] = useState(getUser());
  const isAdmin = isLoggedIn() && sessionUser?.role === "admin";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => subscribe(() => setSessionUser(getUser())), []);

  useEffect(() => {
    if (!isAdmin) {
      setLoading(false);
      return;
    }
    getAnalytics()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin]);

  if (!isAdmin) {
    return (
      <AppShell variant="admin" active="admin-analytics" title="Platform analytics">
        <ErrorMessage error={{ message: "" }}>
          <Link to="/login">Log in</Link> with an admin account to view analytics.
        </ErrorMessage>
      </AppShell>
    );
  }

  return (
    <AppShell
      variant="admin"
      active="admin-analytics"
      title="Platform analytics"
      subtitle="Real, deterministic counts from the platform's own data — no estimates."
    >
      {loading && <LoadingMessage>Loading analytics…</LoadingMessage>}
      {error && <ErrorMessage error={error} />}

      {data && (
        <>
          <div className="stat-grid">
            <StatCard label="Citizens" value={data.total_citizens} />
            <StatCard label="Active schemes" value={data.total_active_schemes} />
            <StatCard label="Eligibility evaluations" value={data.total_eligibility_evaluations} />
            <StatCard label="Bundles generated" value={data.total_bundles_generated} />
            <StatCard label="Open grievances" value={data.open_grievances} />
            <StatCard label="Resolved grievances" value={data.resolved_grievances} />
            <StatCard label="Fraud flags pending review" value={data.fraud_flags_pending_review} />
            <StatCard label="Fraud flags reviewed" value={data.fraud_flags_reviewed} />
            <StatCard label="RAG candidates pending" value={data.rag_candidates_pending} />
          </div>

          <div className="card">
            <h2>Schemes by category</h2>
            {data.schemes_by_category.length === 0 && <p className="hint">No active schemes yet.</p>}
            {data.schemes_by_category.map((c) => (
              <div className="scheme-row" key={c.category}>
                <span>{c.category}</span>
                <strong>{c.count}</strong>
              </div>
            ))}
          </div>

          <div className="card">
            <h2>Most-saved schemes</h2>
            {data.most_saved_schemes.length === 0 && <p className="hint">No schemes saved yet.</p>}
            {data.most_saved_schemes.map((s) => (
              <div className="scheme-row" key={s.scheme_id}>
                <span>{s.scheme_name}</span>
                <strong>{s.save_count}</strong>
              </div>
            ))}
          </div>
        </>
      )}
    </AppShell>
  );
}
