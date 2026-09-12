import { useEffect, useState } from "react";
import { getSchemeDeadline } from "../api/client";

// Honesty-first, same spirit as ApplyLink: only ever shows a deadline that was actually
// extracted from policy text — never a guessed or invented date.
export default function DeadlineBadge({ schemeId }) {
  const [deadline, setDeadline] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getSchemeDeadline(schemeId)
      .then((d) => {
        if (!cancelled) setDeadline(d);
      })
      .catch(() => {
        if (!cancelled) setDeadline(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [schemeId]);

  if (loading) {
    return <p className="hint scheme-card-deadline">Checking application deadline…</p>;
  }

  if (!deadline || !deadline.available) {
    return (
      <p className="hint scheme-card-deadline">
        {deadline?.reason || "No verified application deadline on file for this scheme yet."}
      </p>
    );
  }

  return (
    <p className="scheme-card-deadline">
      <strong>Deadline:</strong> {deadline.deadline_text}
    </p>
  );
}
