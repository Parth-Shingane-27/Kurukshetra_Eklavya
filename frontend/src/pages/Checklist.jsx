import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { generateChecklist } from "../api/client";
import JourneyNav from "../components/JourneyNav";
import StatusBadge from "../components/StatusBadge";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";

export default function Checklist() {
  const { bundleId } = useParams();
  const [searchParams] = useSearchParams();
  const citizenId = searchParams.get("citizen");
  const navigate = useNavigate();
  const [{ loading, error, checklist }, setState] = useState({ loading: true, error: null, checklist: null });

  const run = useCallback(() => {
    let cancelled = false;
    setState({ loading: true, error: null, checklist: null });
    generateChecklist(bundleId)
      .then((data) => {
        if (!cancelled) setState({ loading: false, error: null, checklist: data });
      })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, error: err, checklist: null });
      });
    return () => {
      cancelled = true;
    };
  }, [bundleId]);

  useEffect(() => run(), [run]);

  const items = checklist?.checklist_items ?? [];
  const nothingMissing = items.length > 0 && items.every((i) => i.status === "held");

  return (
    <>
      <JourneyNav current="checklist" citizenId={citizenId} bundleId={bundleId} />
      <main className="page">
        <div className="page-header">
          <h1>Your application checklist</h1>
          <p>Everything you need to apply, consolidated across your recommended schemes.</p>
        </div>

        {loading && <LoadingMessage>Building your checklist…</LoadingMessage>}
        {error && error.status === 404 && <ErrorMessage error={error} onRetry={run} />}
        {error && error.status !== 404 && (
          <ErrorMessage error={error} onRetry={run}>
            {error.status ? "Something went wrong generating your checklist. Please try again." : undefined}
          </ErrorMessage>
        )}

        {checklist && items.length === 0 && (
          <InfoMessage>No documents are required — there&apos;s nothing to prepare.</InfoMessage>
        )}

        {checklist && nothingMissing && (
          <InfoMessage>No documents missing — you already have everything you need.</InfoMessage>
        )}

        {items.length > 0 && (
          <div className="card">
            <h2>Consolidated checklist</h2>
            {items.map((item) => (
              <div className="checklist-item" key={item.document_type}>
                <div>
                  <strong>{item.document_type}</strong>
                  <div className="schemes">Needed for: {item.related_scheme_names.join(", ")}</div>
                </div>
                <StatusBadge status={item.status} />
              </div>
            ))}
          </div>
        )}

        {checklist && (
          <div className="actions">
            <button className="secondary" onClick={() => window.print()}>
              Print checklist
            </button>
            {citizenId && (
              <button className="secondary" onClick={() => navigate(`/citizens/${citizenId}/trace`)}>
                View reasoning trace →
              </button>
            )}
          </div>
        )}
      </main>
    </>
  );
}
