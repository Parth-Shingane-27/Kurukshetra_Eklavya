import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { evaluateEligibility } from "../api/client";
import AppShell from "../components/layout/AppShell";
import ApplyLink from "../components/ApplyLink";
import DeadlineBadge from "../components/DeadlineBadge";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import { ErrorMessage, LoadingMessage } from "../components/StateMessage";
import { humanizeReason } from "../lib/reasonText";

const STATUS_FILTERS = [
  { value: "", label: "All statuses" },
  { value: "eligible", label: "Likely eligible" },
  { value: "indeterminate", label: "Needs verification" },
  { value: "not_eligible", label: "Not currently matched" },
];

export default function EligibleSchemes() {
  const { citizenId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  // The Dashboard already ran this exact evaluation for its "recommended bundle" section — if
  // it handed the results along via navigation state, reuse them instead of silently re-running
  // eligibility evaluation (and re-appending to agent_audit_logs) a second time for the same
  // click-through. Direct navigation (a bookmark, a page refresh, Dashboard skipped) has no
  // state, so it still fetches fresh exactly as before.
  const preloaded = location.state?.results;
  const [{ loading, error, results }, setState] = useState(
    preloaded ? { loading: false, error: null, results: preloaded } : { loading: true, error: null, results: null }
  );
  const [analyzedAt, setAnalyzedAt] = useState(preloaded ? new Date() : null);
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const run = useCallback(() => {
    let cancelled = false;
    setState({ loading: true, error: null, results: null });
    evaluateEligibility(citizenId)
      .then((data) => {
        if (!cancelled) {
          setState({ loading: false, error: null, results: data.results });
          setAnalyzedAt(new Date());
        }
      })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, error: err, results: null });
      });
    return () => {
      cancelled = true;
    };
  }, [citizenId]);

  useEffect(() => {
    if (preloaded) return undefined; // already have results from Dashboard — nothing to fetch
    return run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run]);

  const filteredResults = useMemo(() => {
    if (!results) return [];
    const q = searchText.trim().toLowerCase();
    return results.filter((r) => {
      if (statusFilter && r.status !== statusFilter) return false;
      if (q && !r.scheme_name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [results, searchText, statusFilter]);

  const hasEligible = !!results && results.some((r) => r.status === "eligible");

  return (
    <AppShell
      active="eligibility"
      title="Your Eligibility Results"
      subtitle="Based on the information in your profile, these schemes may be relevant to you."
      meta={analyzedAt && `Analyzed ${analyzedAt.toLocaleTimeString()}`}
      actions={
        <button type="button" className="secondary small" onClick={run} disabled={loading}>
          Re-analyze
        </button>
      }
    >
      {loading && <LoadingMessage>Evaluating your profile…</LoadingMessage>}

      {error && error.status === 409 && (
        <ErrorMessage onRetry={run}>
          We couldn&apos;t evaluate any scheme with the information you gave us — every scheme needs at
          least one more field than you provided. Go back and add a few more details to your profile.
        </ErrorMessage>
      )}
      {error && error.status === 404 && <ErrorMessage error={error} onRetry={run} />}
      {error && error.status !== 409 && error.status !== 404 && (
        <ErrorMessage error={error} onRetry={run}>
          {error.status ? "Something went wrong evaluating your eligibility. Please try again." : undefined}
        </ErrorMessage>
      )}

      {results && !hasEligible && (
        <EmptyState
          icon="◇"
          title="No schemes matched"
          description="Consider updating your profile with more details to widen your match."
          actionLabel="Update profile"
          onAction={() => navigate("/profile")}
        />
      )}

      {results && results.length > 0 && (
        <>
          <div className="explore-controls">
            <input
              type="search"
              className="search-input"
              placeholder="Search by scheme name…"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              aria-label="Search schemes"
            />
            <div className="filter-panel-header">
              {STATUS_FILTERS.map((f) => (
                <button
                  key={f.value}
                  type="button"
                  className={`chip-toggle${statusFilter === f.value ? " active" : ""}`}
                  style={statusFilter === f.value ? { borderColor: "var(--accent)", color: "var(--accent)" } : undefined}
                  onClick={() => setStatusFilter(f.value)}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          <div className="scheme-grid">
            {filteredResults.map((r) => (
              <article className={`scheme-card${r.status === "eligible" ? " emphasis" : ""}`} key={r.scheme_id}>
                <div className="scheme-card-top">
                  <StatusBadge status={r.status} />
                </div>
                <h3>{r.scheme_name}</h3>
                {r.reasons.length > 0 && (
                  <div className="reasons">
                    <ul>
                      {r.reasons.map((reason, i) => (
                        <li key={i}>{humanizeReason(reason)}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <DeadlineBadge schemeId={r.scheme_id} />
                {r.status === "eligible" && (
                  <ApplyLink url={r.application_url} status={r.application_link_status} schemeId={r.scheme_id} />
                )}
              </article>
            ))}
          </div>

          {filteredResults.length === 0 && (
            <EmptyState icon="◇" title="No schemes match your filters" description="Try clearing the search or status filter." />
          )}
        </>
      )}

      {results && (
        <div className="actions">
          <button
            onClick={() =>
              navigate(`/citizens/${citizenId}/bundle`, {
                // Forward whatever Dashboard-computed bundle/conflicts arrived with this
                // screen (may be undefined if this screen was reached directly, e.g. a
                // bookmark) so Bundle can also skip re-fetching when it's available.
                state: {
                  bundle: location.state?.bundle,
                  schemes: location.state?.schemes,
                  conflicts: location.state?.conflicts,
                },
              })
            }
          >
            See my optimized bundle →
          </button>
        </div>
      )}
    </AppShell>
  );
}
