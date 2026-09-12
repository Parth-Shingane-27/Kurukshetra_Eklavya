import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  approveRagCandidate,
  approveSchemeDiscovery,
  listRagCandidates,
  listSchemeDiscoveries,
  listSchemes,
  rejectRagCandidate,
  rejectSchemeDiscovery,
  searchSchemeDiscovery,
  triggerRagRefresh,
} from "../api/client";
import { getUser, isLoggedIn, subscribe } from "../auth/session";
import AppShell from "../components/layout/AppShell";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";

// FR-015 — RAG-Based Knowledge Base Freshness admin review queue. Candidates are proposals
// only (BR-015) — nothing here is ever committed to a scheme except through the explicit
// Approve action, which reuses the same update_scheme path FR-011's manual edit form uses.
export default function RagCandidates() {
  const [sessionUser, setSessionUser] = useState(getUser());
  const isAdmin = isLoggedIn() && sessionUser?.role === "admin";

  const [schemes, setSchemes] = useState([]);
  const [refreshSchemeId, setRefreshSchemeId] = useState("");
  const [refreshMessage, setRefreshMessage] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState(null);

  const [statusFilter, setStatusFilter] = useState("pending");
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [rejectingId, setRejectingId] = useState(null);
  const [rejectReason, setRejectReason] = useState("");

  const [discoveryQuery, setDiscoveryQuery] = useState("");
  const [discoveryCategory, setDiscoveryCategory] = useState("");
  const [discovering, setDiscovering] = useState(false);
  const [discoveryMessage, setDiscoveryMessage] = useState(null);
  const [discoveryError, setDiscoveryError] = useState(null);

  const [discoveryStatusFilter, setDiscoveryStatusFilter] = useState("pending");
  const [discoveries, setDiscoveries] = useState([]);
  const [discoveriesLoading, setDiscoveriesLoading] = useState(true);
  const [discoveriesLoadError, setDiscoveriesLoadError] = useState(null);
  const [discoveryActionError, setDiscoveryActionError] = useState(null);
  const [rejectingDiscoveryId, setRejectingDiscoveryId] = useState(null);
  const [discoveryRejectReason, setDiscoveryRejectReason] = useState("");

  useEffect(() => subscribe(() => setSessionUser(getUser())), []);

  useEffect(() => {
    listSchemes().then(setSchemes).catch(() => {});
  }, []);

  const loadCandidates = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listRagCandidates({ status: statusFilter || undefined });
      setCandidates(data);
      setLoadError(null);
    } catch (err) {
      setLoadError(err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadCandidates();
  }, [loadCandidates]);

  async function handleRefresh(e) {
    e.preventDefault();
    if (!refreshSchemeId) return;
    setRefreshing(true);
    setRefreshError(null);
    setRefreshMessage(null);
    try {
      const result = await triggerRagRefresh(refreshSchemeId);
      if (result.candidate) {
        setRefreshMessage("New candidate update created — see the queue below.");
        loadCandidates();
      } else {
        setRefreshMessage(result.message || "No confident candidate update could be produced for this scheme.");
      }
    } catch (err) {
      setRefreshError(err);
    } finally {
      setRefreshing(false);
    }
  }

  async function handleApprove(id) {
    setActionError(null);
    try {
      await approveRagCandidate(id);
      loadCandidates();
    } catch (err) {
      setActionError(err);
    }
  }

  async function handleReject(id) {
    setActionError(null);
    try {
      await rejectRagCandidate(id, rejectReason.trim() || undefined);
      setRejectingId(null);
      setRejectReason("");
      loadCandidates();
    } catch (err) {
      setActionError(err);
    }
  }

  const loadDiscoveries = useCallback(async () => {
    setDiscoveriesLoading(true);
    try {
      const data = await listSchemeDiscoveries(discoveryStatusFilter || undefined);
      setDiscoveries(data);
      setDiscoveriesLoadError(null);
    } catch (err) {
      setDiscoveriesLoadError(err);
    } finally {
      setDiscoveriesLoading(false);
    }
  }, [discoveryStatusFilter]);

  useEffect(() => {
    loadDiscoveries();
  }, [loadDiscoveries]);

  async function handleDiscoverySearch(e) {
    e.preventDefault();
    if (!discoveryQuery.trim()) return;
    setDiscovering(true);
    setDiscoveryError(null);
    setDiscoveryMessage(null);
    try {
      const results = await searchSchemeDiscovery(discoveryQuery.trim(), discoveryCategory.trim());
      if (results.length > 0) {
        setDiscoveryMessage(`Found ${results.length} candidate scheme(s) — see the queue below.`);
        loadDiscoveries();
      } else {
        setDiscoveryMessage("No new, confidently-sourced schemes were found for this search.");
      }
    } catch (err) {
      setDiscoveryError(err);
    } finally {
      setDiscovering(false);
    }
  }

  async function handleApproveDiscovery(id) {
    setDiscoveryActionError(null);
    try {
      await approveSchemeDiscovery(id);
      loadDiscoveries();
    } catch (err) {
      setDiscoveryActionError(err);
    }
  }

  async function handleRejectDiscovery(id) {
    setDiscoveryActionError(null);
    try {
      await rejectSchemeDiscovery(id, discoveryRejectReason.trim() || undefined);
      setRejectingDiscoveryId(null);
      setDiscoveryRejectReason("");
      loadDiscoveries();
    } catch (err) {
      setDiscoveryActionError(err);
    }
  }

  const schemeOptions = [{ value: "", label: "Select a scheme…" }, ...schemes.map((s) => ({ value: s.id, label: s.name }))];

  return (
    <AppShell
      variant="admin"
      active="admin-rag"
      title="RAG knowledge-base freshness queue"
      subtitle="Retrieval-drafted candidate updates for curator review (FR-015). Nothing here is ever applied to the live scheme catalogue until you explicitly approve it."
    >
      <div className="card">
        {isAdmin ? (
          <InfoMessage>Logged in as {sessionUser.email} (admin).</InfoMessage>
        ) : (
          <InfoMessage>
            <Link to="/login">Log in</Link> with an admin account to trigger refreshes or review
            candidates.
          </InfoMessage>
        )}
      </div>

      {isAdmin && (
        <form className="card" onSubmit={handleRefresh}>
          <h2>Refresh a scheme</h2>
          <div className="form-grid">
            <label>
              Scheme
              <select value={refreshSchemeId} onChange={(e) => setRefreshSchemeId(e.target.value)}>
                {schemeOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="actions">
            <button type="submit" disabled={refreshing || !refreshSchemeId}>
              {refreshing ? "Retrieving…" : "Retrieve & draft candidate update"}
            </button>
          </div>
          {refreshMessage && <InfoMessage>{refreshMessage}</InfoMessage>}
          {refreshError && <ErrorMessage error={refreshError} />}
        </form>
      )}

      {isAdmin && (
        <form className="card" onSubmit={handleDiscoverySearch}>
          <h2>Discover new schemes (live web search)</h2>
          <p className="hint">
            Searches the internet for real government schemes not yet in the catalogue. Nothing
            is added to the catalogue until you explicitly approve a discovered scheme below —
            approved schemes always start with an unverified application link.
          </p>
          <div className="form-grid">
            <label>
              Search query
              <input
                type="text"
                placeholder="e.g. scholarship for farmers' daughters in Maharashtra"
                value={discoveryQuery}
                onChange={(e) => setDiscoveryQuery(e.target.value)}
              />
            </label>
            <label>
              Category (optional)
              <input
                type="text"
                placeholder="e.g. education"
                value={discoveryCategory}
                onChange={(e) => setDiscoveryCategory(e.target.value)}
              />
            </label>
          </div>
          <div className="actions">
            <button type="submit" disabled={discovering || !discoveryQuery.trim()}>
              {discovering ? "Searching…" : "Search the web"}
            </button>
          </div>
          {discoveryMessage && <InfoMessage>{discoveryMessage}</InfoMessage>}
          {discoveryError && <ErrorMessage error={discoveryError} />}
        </form>
      )}

      <div className="card">
        <div className="scheme-row">
          <h2>Discovered scheme queue</h2>
          <select value={discoveryStatusFilter} onChange={(e) => setDiscoveryStatusFilter(e.target.value)}>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="">All</option>
          </select>
        </div>

        {discoveriesLoading && <LoadingMessage>Loading discovered schemes…</LoadingMessage>}
        {discoveriesLoadError && <ErrorMessage error={discoveriesLoadError} onRetry={loadDiscoveries} />}
        {discoveryActionError && <ErrorMessage error={discoveryActionError} />}
        {!discoveriesLoading && discoveries.length === 0 && (
          <InfoMessage>No discovered schemes in this status.</InfoMessage>
        )}

        {discoveries.map((d) => (
          <div className="card catalog-item" key={d.id}>
            <div className="scheme-row">
              <div>
                <strong>{d.draft?.name}</strong>
                <p className="hint">
                  Status: {d.status} · Confidence: {(d.confidence * 100).toFixed(0)}% · Query: "{d.query}"
                </p>
              </div>
            </div>

            <p>{d.rationale}</p>
            {d.draft?.description && <p>{d.draft.description}</p>}

            <div className="reasons">
              <p className="hint">Drafted details:</p>
              <ul>
                {d.draft?.issuing_authority && <li>Issuing authority: {d.draft.issuing_authority}</li>}
                {d.draft?.category && <li>Category: {d.draft.category}</li>}
                {d.draft?.benefit_type && <li>Benefit type: {d.draft.benefit_type}</li>}
                {d.draft?.benefit_value_estimate != null && (
                  <li>Estimated benefit value: {d.draft.benefit_value_estimate}</li>
                )}
                {d.draft?.links?.official_scheme_url && (
                  <li>
                    Official page:{" "}
                    <a href={d.draft.links.official_scheme_url} target="_blank" rel="noreferrer">
                      {d.draft.links.official_scheme_url}
                    </a>
                  </li>
                )}
                {d.draft?.links?.application_url && (
                  <li>
                    Application link (unverified):{" "}
                    <a href={d.draft.links.application_url} target="_blank" rel="noreferrer">
                      {d.draft.links.application_url}
                    </a>
                  </li>
                )}
              </ul>
            </div>

            <div className="reasons">
              <p className="hint">Source passages:</p>
              <ul>
                {d.source_passages.map((p, i) => (
                  <li key={i}>
                    {p.content}
                    {p.source_url && (
                      <>
                        {" — "}
                        <a href={p.source_url} target="_blank" rel="noreferrer">
                          source ↗
                        </a>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {isAdmin && d.status === "pending" && (
              <div className="actions">
                <button type="button" onClick={() => handleApproveDiscovery(d.id)}>
                  Approve &amp; add to catalogue
                </button>
                {rejectingDiscoveryId === d.id ? (
                  <>
                    <input
                      type="text"
                      placeholder="Rejection reason (optional)"
                      value={discoveryRejectReason}
                      onChange={(e) => setDiscoveryRejectReason(e.target.value)}
                    />
                    <button type="button" className="secondary" onClick={() => handleRejectDiscovery(d.id)}>
                      Confirm reject
                    </button>
                  </>
                ) : (
                  <button type="button" className="secondary" onClick={() => setRejectingDiscoveryId(d.id)}>
                    Reject
                  </button>
                )}
              </div>
            )}

            {d.status === "rejected" && d.rejection_reason && <p className="hint">Rejected: {d.rejection_reason}</p>}
          </div>
        ))}
      </div>

      <div className="card">
        <div className="scheme-row">
          <h2>Candidate queue</h2>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="">All</option>
          </select>
        </div>

        {loading && <LoadingMessage>Loading candidates…</LoadingMessage>}
        {loadError && <ErrorMessage error={loadError} onRetry={loadCandidates} />}
        {actionError && <ErrorMessage error={actionError} />}
        {!loading && candidates.length === 0 && <InfoMessage>No candidates in this status.</InfoMessage>}

        {candidates.map((c) => (
          <div className="card catalog-item" key={c.id}>
            <div className="scheme-row">
              <div>
                <strong>{c.scheme_name}</strong>
                <p className="hint">
                  Status: {c.status} · Confidence: {(c.confidence * 100).toFixed(0)}%
                </p>
              </div>
            </div>

            <p>{c.rationale}</p>

            <div className="reasons">
              <p className="hint">Proposed changes:</p>
              <ul>
                {Object.entries(c.proposed_changes).map(([key, value]) => (
                  <li key={key}>
                    <strong>{key}</strong>: {Array.isArray(value) ? value.join(", ") : String(value)}
                    {" "}
                    <span className="hint">
                      (currently: {String(c.current_snapshot?.[key] ?? "none on file")})
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="reasons">
              <p className="hint">Source passages:</p>
              <ul>
                {c.source_passages.map((p, i) => (
                  <li key={i}>
                    {p.content}
                    {p.source_url && (
                      <>
                        {" — "}
                        <a href={p.source_url} target="_blank" rel="noreferrer">
                          source ↗
                        </a>
                      </>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {isAdmin && c.status === "pending" && (
              <div className="actions">
                <button type="button" onClick={() => handleApprove(c.id)}>
                  Approve
                </button>
                {rejectingId === c.id ? (
                  <>
                    <input
                      type="text"
                      placeholder="Rejection reason (optional)"
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                    />
                    <button type="button" className="secondary" onClick={() => handleReject(c.id)}>
                      Confirm reject
                    </button>
                  </>
                ) : (
                  <button type="button" className="secondary" onClick={() => setRejectingId(c.id)}>
                    Reject
                  </button>
                )}
              </div>
            )}

            {c.status === "rejected" && c.rejection_reason && (
              <p className="hint">Rejected: {c.rejection_reason}</p>
            )}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
