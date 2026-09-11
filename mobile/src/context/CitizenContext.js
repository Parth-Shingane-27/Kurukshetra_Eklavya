import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { getCitizen } from "../lib/api";
import { getStoredCitizenId } from "../lib/storage";

// Shared across the Home and Explore tabs so both read the same citizen profile without each
// re-fetching it independently.
const CitizenContext = createContext(null);

export function CitizenProvider({ children }) {
  const [state, setState] = useState({ loading: true, error: null, citizen: null, citizenId: null });

  const reload = useCallback(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    (async () => {
      const citizenId = await getStoredCitizenId();
      if (!citizenId) {
        if (!cancelled) setState({ loading: false, error: null, citizen: null, citizenId: null });
        return;
      }
      try {
        const citizen = await getCitizen(citizenId);
        if (!cancelled) setState({ loading: false, error: null, citizen, citizenId });
      } catch (err) {
        if (!cancelled) setState({ loading: false, error: err, citizen: null, citizenId });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => reload(), [reload]);

  return <CitizenContext.Provider value={{ ...state, reload }}>{children}</CitizenContext.Provider>;
}

export function useCitizen() {
  const ctx = useContext(CitizenContext);
  if (!ctx) throw new Error("useCitizen must be used within a CitizenProvider");
  return ctx;
}
