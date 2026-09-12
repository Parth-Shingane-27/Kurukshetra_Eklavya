import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { detectConflicts, getScheme, optimizeBundle } from "../api/client";
import AppShell from "../components/layout/AppShell";
import ApplyLink from "../components/ApplyLink";
import DeadlineBadge from "../components/DeadlineBadge";
import EmptyState from "../components/EmptyState";
import StatCard from "../components/StatCard";
import { ErrorMessage, LoadingMessage } from "../components/StateMessage";
import { setStoredBundleId } from "../lib/storage";

function categoryChipClass(index) {
  return `category-chip category-chip-${index % 3}`;
}

export default function Bundle() {
  const { citizenId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  // Reuse the Dashboard's already-computed bundle/conflicts (passed via navigation state) if
  // present, instead of re-running conflict detection + bundle optimization — and re-appending
  // to agent_audit_logs — a second time for the same click-through. Direct navigation has no
  // state, so it still fetches fresh exactly as before.
  const preloadedBundle = location.state?.bundle;
  const [{ loading, error, bundle, schemes, conflicts }, setState] = useState(
    preloadedBundle
      ? {
          loading: false,
          error: null,
          bundle: preloadedBundle,
          schemes: location.state?.schemes || [],
          conflicts: location.state?.conflicts || [],
        }
      : { loading: true, error: null, bundle: null, schemes: [], conflicts: [] }
  );

  const run = useCallback(() => {
    let cancelled = false;
    setState({ loading: true, error: null, bundle: null, schemes: [], conflicts: [] });

    (async () => {
      try {
        const conflictData = await detectConflicts(citizenId);
        const bundleData = await optimizeBundle(citizenId);
        const schemeDetails = await Promise.all(bundleData.scheme_ids.map((id) => getScheme(id)));
        if (!cancelled) {
          setState({
            loading: false,
            error: null,
            bundle: bundleData,
            schemes: schemeDetails,
            conflicts: conflictData.conflicts,
          });
        }
      } catch (err) {
        if (!cancelled) setState({ loading: false, error: err, bundle: null, schemes: [], conflicts: [] });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [citizenId]);

  useEffect(() => {
    if (preloadedBundle) return undefined; // already have Dashboard's results — nothing to fetch
    return run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run]);

  useEffect(() => {
    if (bundle?.bundle_id) setStoredBundleId(bundle.bundle_id);
  }, [bundle]);

  const grouped = useMemo(() => {
    const groups = new Map();
    schemes.forEach((s) => {
      const cats = (s.category || "Uncategorized").split(",").map((c) => c.trim()).filter(Boolean);
      const key = cats[0] || "Uncategorized";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(s);
    });
    return [...groups.entries()];
  }, [schemes]);

  return (
    <AppShell
      active="bundle"
      title="Your Optimized Support Bundle"
      subtitle="We evaluated potentially eligible schemes, checked compatibility, and selected a combination that best fits your current needs."
    >
      {loading && <LoadingMessage>Checking for conflicts and optimizing your bundle…</LoadingMessage>}

      {error && error.status === 422 && (
        <ErrorMessage onRetry={run}>
          We need to evaluate your eligibility first.{" "}
          <button className="secondary" onClick={() => navigate(`/citizens/${citizenId}/eligibility`)}>
            Go back
          </button>
        </ErrorMessage>
      )}
      {error && error.status === 404 && <ErrorMessage error={error} onRetry={run} />}
      {error && error.status !== 422 && error.status !== 404 && (
        <ErrorMessage error={error} onRetry={run}>
          {error.status ? "Something went wrong computing your bundle. Please try again." : undefined}
        </ErrorMessage>
      )}

      {bundle && bundle.scheme_ids.length === 0 && (
        <EmptyState icon="◇" title="No viable bundle" description="None of the schemes you're eligible for could be included together." />
      )}

      {bundle && schemes.length > 0 && (
        <>
          <div className="stat-card-row">
            <StatCard label="Selected schemes" value={schemes.length} />
            <StatCard label="Categories covered" value={grouped.length} />
            <StatCard label="Compatibility status" value={conflicts.length ? "Reviewed" : "Compatible"} context={`${conflicts.length} flagged`} />
            <StatCard label="Total estimated benefit" value={`₹${bundle.total_benefit_value.toLocaleString()}`} />
          </div>

          <h2>Selected schemes by category</h2>
          {grouped.map(([category, catSchemes], i) => (
            <div className="category-group" key={category}>
              <div className="category-group-header">
                <span className={categoryChipClass(i)}>{category}</span>
                <span className="hint">{catSchemes.length} scheme{catSchemes.length === 1 ? "" : "s"}</span>
              </div>
              <div className="scheme-grid">
                {catSchemes.map((s) => (
                  <article className="scheme-card" key={s.id}>
                    <h3>{s.name}</h3>
                    <div className="scheme-card-benefit">
                      ₹{s.benefit_value_estimate.toLocaleString()}
                      <span> · {s.benefit_type.replaceAll("_", " ")}</span>
                    </div>
                    <DeadlineBadge schemeId={s.id} />
                    <ApplyLink
                      url={s.links?.application_url}
                      status={s.links?.application_link_status}
                      moreInfoUrl={s.links?.official_scheme_url}
                      schemeId={s.id}
                    />
                  </article>
                ))}
              </div>
            </div>
          ))}
        </>
      )}

      {bundle && bundle.explanation_text && (
        <div className="card">
          <h2>Why this bundle?</h2>
          <div className="explanation">{bundle.explanation_text}</div>
        </div>
      )}

      <h2>Compatibility review</h2>
      {conflicts.length === 0 ? (
        <EmptyState icon="✓" title="No conflicts detected" description="Every scheme in this bundle can be held together under the configured rules." />
      ) : (
        conflicts.map((c, i) => (
          <div className="conflict-card" key={i}>
            <span className="conflict-card-icon" aria-hidden="true">⚠</span>
            <div>
              <strong>{c.scheme_a_name} + {c.scheme_b_name}</strong>
              <p>{c.reason}</p>
            </div>
          </div>
        ))
      )}

      {bundle && bundle.excluded.length > 0 && (
        <>
          <h2>Other combinations considered</h2>
          <p className="hint">These schemes were left out of your optimized bundle — here's why.</p>
          {bundle.excluded.map((e) => (
            <div className="excluded-card" key={e.scheme_id}>
              <strong>{e.scheme_name}</strong>
              <p className="hint" style={{ margin: "0.2rem 0 0" }}>{e.reason}</p>
            </div>
          ))}
        </>
      )}

      {bundle && (
        <div className="actions">
          <button onClick={() => navigate(`/bundles/${bundle.bundle_id}/checklist?citizen=${citizenId}`)}>
            View Application Plan →
          </button>
        </div>
      )}
    </AppShell>
  );
}
