import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAllFraudFlags, listSchemes, reviewFraudFlag, screenCitizenForFraud } from "../api/client";
import { getUser, isLoggedIn, subscribe } from "../auth/session";
import AppShell from "../components/layout/AppShell";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import StatusBadge from "../components/StatusBadge";

// Fraud Detection — an internal, admin-only trust-and-safety review queue. Deterministic
// indicators only (document-type mismatch, missing fields, expired documents, duplicates,
// cross-document conflicts) surfaced for a human to review — this page never asserts
// "confirmed fraud," only a risk level and indicators requiring a human decision.
export default function AdminFraud() {
  const [sessionUser, setSessionUser] = useState(getUser());
  const isAdmin = isLoggedIn() && sessionUser?.role === "admin";

  const [screenCitizenId, setScreenCitizenId] = useState("");
  const [screenSchemeId, setScreenSchemeId] = useState("");
  const [schemes, setSchemes] = useState([]);
  const [screening, setScreening] = useState(false);
  const [screenError, setScreenError] = useState(null);
  const [screenMessage, setScreenMessage] = useState(null);

  const [reviewedFilter, setReviewedFilter] = useState("false");
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [reviewingId, setReviewingId] = useState(null);
  const [reviewerNotes, setReviewerNotes] = useState("");

  useEffect(() => subscribe(() => setSessionUser(getUser())), []);
  useEffect(() => {
    listSchemes().then(setSchemes).catch(() => {});
  }, []);

  const loadFlags = useCallback(() => {
    setLoading(true);
    const reviewed = reviewedFilter === "" ? undefined : reviewedFilter === "true";
    listAllFraudFlags({ reviewed })
      .then(setFlags)
      .catch(setLoadError)
      .finally(() => setLoading(false));
  }, [reviewedFilter]);

  useEffect(() => loadFlags(), [loadFlags]);

  async function handleScreen(e) {
    e.preventDefault();
    if (!screenCitizenId.trim()) return;
    setScreening(true);
    setScreenError(null);
    setScreenMessage(null);
    try {
      await screenCitizenForFraud(screenCitizenId.trim(), screenSchemeId || undefined);
      setScreenMessage("Screening complete — see the queue below.");
      loadFlags();
    } catch (err) {
      setScreenError(err);
    } finally {
      setScreening(false);
    }
  }

  async function handleReview(id) {
    if (!reviewerNotes.trim()) return;
    setActionError(null);
    try {
      await reviewFraudFlag(id, reviewerNotes.trim());
      setReviewingId(null);
      setReviewerNotes("");
      loadFlags();
    } catch (err) {
      setActionError(err);
    }
  }

  return (
    <AppShell
      variant="admin"
      active="admin-fraud"
      title="Fraud & document-consistency review"
      subtitle="Deterministic risk indicators from document verification checks — not a fraud determination. Every flag needs a human decision before it means anything."
    >
      <div className="card">
        {isAdmin ? (
          <InfoMessage>Logged in as {sessionUser.email} (admin).</InfoMessage>
        ) : (
          <InfoMessage>
            <Link to="/login">Log in</Link> with an admin account to screen citizens or review flags.
          </InfoMessage>
        )}
      </div>

      {isAdmin && (
        <form className="card" onSubmit={handleScreen}>
          <h2>Screen a citizen</h2>
          <div className="form-grid">
            <label>
              Citizen ID
              <input type="text" value={screenCitizenId} onChange={(e) => setScreenCitizenId(e.target.value)} />
            </label>
            <label>
              Scheme (optional — narrows to one scheme's document checks)
              <select value={screenSchemeId} onChange={(e) => setScreenSchemeId(e.target.value)}>
                <option value="">All schemes</option>
                {schemes.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="actions">
            <button type="submit" disabled={screening || !screenCitizenId.trim()}>
              {screening ? "Screening…" : "Run screening"}
            </button>
          </div>
          {screenMessage && <InfoMessage>{screenMessage}</InfoMessage>}
          {screenError && <ErrorMessage error={screenError} />}
        </form>
      )}

      <div className="card">
        <div className="scheme-row">
          <h2>Review queue</h2>
          <select value={reviewedFilter} onChange={(e) => setReviewedFilter(e.target.value)}>
            <option value="false">Not yet reviewed</option>
            <option value="true">Reviewed</option>
            <option value="">All</option>
          </select>
        </div>

        {loading && <LoadingMessage>Loading flags…</LoadingMessage>}
        {loadError && <ErrorMessage error={loadError} onRetry={loadFlags} />}
        {actionError && <ErrorMessage error={actionError} />}
        {!loading && flags.length === 0 && <InfoMessage>No flags in this status.</InfoMessage>}

        {flags.map((f) => (
          <div className="card catalog-item" key={f.id}>
            <div className="scheme-row">
              <div>
                <strong>Citizen: {f.citizen_id}</strong>
                <p className="hint">{f.scheme_id ? `Scheme: ${f.scheme_id}` : "All schemes"}</p>
                <p>{f.summary}</p>
              </div>
              <StatusBadge status={f.risk_level} />
            </div>

            {f.indicators.length > 0 && (
              <ul className="reasons">
                {f.indicators.map((ind, i) => (
                  <li key={i}>
                    <strong>{ind.type}</strong>: {ind.detail || JSON.stringify(ind)}
                  </li>
                ))}
              </ul>
            )}

            {f.reviewed ? (
              <p className="hint">Reviewed: {f.reviewer_notes}</p>
            ) : (
              isAdmin && (
                <div className="actions">
                  {reviewingId === f.id ? (
                    <>
                      <input
                        type="text"
                        placeholder="Reviewer notes"
                        value={reviewerNotes}
                        onChange={(e) => setReviewerNotes(e.target.value)}
                      />
                      <button type="button" onClick={() => handleReview(f.id)} disabled={!reviewerNotes.trim()}>
                        Confirm review
                      </button>
                    </>
                  ) : (
                    <button type="button" className="secondary" onClick={() => setReviewingId(f.id)}>
                      Mark reviewed
                    </button>
                  )}
                </div>
              )
            )}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
