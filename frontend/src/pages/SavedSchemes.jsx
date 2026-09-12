import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listSavedSchemes, unsaveScheme } from "../api/client";
import AppShell from "../components/layout/AppShell";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { getStoredCitizenId } from "../lib/storage";

export default function SavedSchemes() {
  const navigate = useNavigate();
  const citizenId = getStoredCitizenId();
  const [saved, setSaved] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    if (!citizenId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    listSavedSchemes(citizenId)
      .then(setSaved)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [citizenId]);

  useEffect(() => load(), [load]);

  async function handleRemove(schemeId) {
    try {
      await unsaveScheme(citizenId, schemeId);
      setSaved((prev) => prev.filter((s) => s.scheme_id !== schemeId));
    } catch (err) {
      setError(err);
    }
  }

  if (!citizenId) {
    return (
      <AppShell active="saved" title="Saved schemes">
        <InfoMessage>Complete your profile first to save schemes for later.</InfoMessage>
      </AppShell>
    );
  }

  return (
    <AppShell
      active="saved"
      title="Saved schemes"
      subtitle="Schemes you've bookmarked to revisit — whether or not you're currently eligible."
    >
      {loading && <LoadingMessage>Loading your saved schemes…</LoadingMessage>}
      {error && <ErrorMessage error={error} onRetry={load} />}
      {!loading && saved.length === 0 && <InfoMessage>You haven't saved any schemes yet.</InfoMessage>}

      <div className="card">
        {saved.map((s) => (
          <div className="scheme-row" key={s.id}>
            <div>
              <strong>{s.scheme_name}</strong>
              <p className="hint">{s.scheme_category}</p>
            </div>
            <div className="actions">
              <button type="button" className="secondary" onClick={() => navigate("/catalog")}>
                View in catalog
              </button>
              <button type="button" className="ghost" onClick={() => handleRemove(s.scheme_id)}>
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
