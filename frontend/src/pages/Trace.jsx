import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getTrace } from "../api/client";
import JourneyNav from "../components/JourneyNav";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";

const STEP_LABELS = {
  eligibility: "Eligibility evaluation",
  conflicts: "Conflict detection",
  bundle_optimization: "Bundle optimization",
  explanation: "Explanation generation",
  checklist: "Checklist generation",
};

export default function Trace() {
  const { citizenId } = useParams();
  const [{ loading, error, steps }, setState] = useState({ loading: true, error: null, steps: null });

  const run = useCallback(() => {
    let cancelled = false;
    setState({ loading: true, error: null, steps: null });
    getTrace(citizenId)
      .then((data) => {
        if (!cancelled) setState({ loading: false, error: null, steps: data.steps });
      })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, error: err, steps: null });
      });
    return () => {
      cancelled = true;
    };
  }, [citizenId]);

  useEffect(() => run(), [run]);

  return (
    <>
      <JourneyNav current="trace" citizenId={citizenId} />
      <main className="page">
        <div className="page-header">
          <h1>Agent reasoning trace</h1>
          <p>Step-by-step record of what the system computed, for full transparency.</p>
        </div>

        {loading && <LoadingMessage>Loading trace…</LoadingMessage>}
        {error && error.status === 404 && <ErrorMessage error={error} onRetry={run} />}
        {error && error.status !== 404 && (
          <ErrorMessage error={error} onRetry={run}>
            {error.status ? "Something went wrong loading the trace. Please try again." : undefined}
          </ErrorMessage>
        )}

        {steps && steps.length === 0 && <InfoMessage>No evaluation run yet.</InfoMessage>}

        {steps &&
          steps.map((step, i) => (
            <details className="trace-step" key={i}>
              <summary>
                <span>{STEP_LABELS[step.step_name] || step.step_name}</span>
                <span>{new Date(step.created_at).toLocaleString()}</span>
              </summary>
              <p>
                <strong>Input</strong>
              </p>
              <pre>{JSON.stringify(step.input_snapshot, null, 2)}</pre>
              <p>
                <strong>Output</strong>
              </p>
              <pre>{JSON.stringify(step.output_snapshot, null, 2)}</pre>
            </details>
          ))}
      </main>
    </>
  );
}
