const LABELS = {
  eligible: "Eligible",
  not_eligible: "Not eligible",
  indeterminate: "Needs more info",
  held: "Held",
  missing: "Missing",
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{LABELS[status] || status}</span>;
}
