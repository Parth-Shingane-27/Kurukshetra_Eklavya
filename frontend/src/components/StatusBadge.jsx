const LABELS = {
  eligible: "Likely eligible",
  not_eligible: "Not currently matched",
  indeterminate: "Needs verification",
  held: "Held",
  missing: "Missing",
  open: "Open",
  resolved: "Resolved",
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{LABELS[status] || status}</span>;
}
