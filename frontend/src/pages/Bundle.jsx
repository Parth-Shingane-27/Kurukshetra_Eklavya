import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { detectConflicts, getScheme, optimizeBundle } from "../api/client";
import JourneyNav from "../components/JourneyNav";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";

export default function Bundle() {
  const { citizenId } = useParams();
  const navigate = useNavigate();
  const [{ loading, error, bundle, schemes, conflicts }, setState] = useState({
    loading: true,
    error: null,
    bundle: null,
    schemes: [],
    conflicts: [],
  });

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

  useEffect(() => run(), [run]);

  return (
    <>
      <JourneyNav current="bundle" citizenId={citizenId} bundleId={bundle?.bundle_id} />
      <main className="page">
        <div className="page-header">
          <h1>Your optimized bundle</h1>
          <p>The best conflict-free combination of schemes for your profile.</p>
        </div>

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
          <InfoMessage>No viable bundle — none of the schemes you&apos;re eligible for could be included.</InfoMessage>
        )}

        {bundle && schemes.length > 0 && (
          <div className="card">
            <h2>Recommended schemes</h2>
            <p className="total-benefit">₹{bundle.total_benefit_value.toLocaleString()}</p>
            <p>total estimated benefit</p>
            {schemes.map((s) => (
              <div className="scheme-row" key={s.id}>
                <div>
                  <strong>{s.name}</strong>
                  <div className="reasons">₹{s.benefit_value_estimate.toLocaleString()} · {s.category}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {conflicts.length > 0 && (
          <div className="card">
            <h2>Conflicts detected</h2>
            {conflicts.map((c, i) => (
              <div className="scheme-row" key={i}>
                <div>
                  <strong>
                    {c.scheme_a_name} vs. {c.scheme_b_name}
                  </strong>
                  <div className="reasons">{c.reason}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {bundle && bundle.excluded.length > 0 && (
          <div className="card">
            <h2>Excluded from your bundle</h2>
            {bundle.excluded.map((e) => (
              <div className="scheme-row" key={e.scheme_id}>
                <div>
                  <strong>{e.scheme_name}</strong>
                  <div className="reasons">{e.reason}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {bundle && bundle.explanation_text && (
          <div className="card">
            <h2>Why this bundle</h2>
            <div className="explanation">{bundle.explanation_text}</div>
          </div>
        )}

        {bundle && (
          <div className="actions">
            <button onClick={() => navigate(`/bundles/${bundle.bundle_id}/checklist?citizen=${citizenId}`)}>
              View my checklist →
            </button>
          </div>
        )}
      </main>
    </>
  );
}
