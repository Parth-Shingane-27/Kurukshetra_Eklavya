import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { evaluateEligibility } from "../api/client";
import JourneyNav from "../components/JourneyNav";
import StatusBadge from "../components/StatusBadge";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";

export default function EligibleSchemes() {
  const { citizenId } = useParams();
  const navigate = useNavigate();
  const [{ loading, error, results }, setState] = useState({ loading: true, error: null, results: null });

  const run = useCallback(() => {
    let cancelled = false;
    setState({ loading: true, error: null, results: null });
    evaluateEligibility(citizenId)
      .then((data) => {
        if (!cancelled) setState({ loading: false, error: null, results: data.results });
      })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, error: err, results: null });
      });
    return () => {
      cancelled = true;
    };
  }, [citizenId]);

  useEffect(() => run(), [run]);

  const hasEligible = !!results && results.some((r) => r.status === "eligible");

  return (
    <>
      <JourneyNav current="eligibility" citizenId={citizenId} />
      <main className="page">
        <div className="page-header">
          <h1>Your eligible schemes</h1>
          <p>We checked your profile against every active scheme in the knowledge base.</p>
        </div>

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
          <InfoMessage>No schemes matched — consider updating your profile with more details.</InfoMessage>
        )}

        {results && results.length > 0 && (
          <div className="card">
            {results.map((r) => (
              <div className="scheme-row" key={r.scheme_id}>
                <div>
                  <strong>{r.scheme_name}</strong>
                  {r.reasons.length > 0 && (
                    <div className="reasons">
                      <ul>
                        {r.reasons.map((reason, i) => (
                          <li key={i}>{reason.message}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {r.status === "eligible" && r.application_link && (
                    <div className="reasons">
                      <a href={r.application_link} target="_blank" rel="noreferrer">
                        Apply on the official portal ↗
                      </a>
                    </div>
                  )}
                </div>
                <StatusBadge status={r.status} />
              </div>
            ))}
          </div>
        )}

        {results && (
          <div className="actions">
            <button onClick={() => navigate(`/citizens/${citizenId}/bundle`)}>
              See my optimized bundle →
            </button>
          </div>
        )}
      </main>
    </>
  );
}
