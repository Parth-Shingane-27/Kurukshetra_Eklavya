export default function StatCard({ label, value, context, onClick, actionLabel, icon, tone }) {
  return (
    <div className={`stat-card${tone ? ` stat-card-tone-${tone}` : ""}`}>
      {icon && <span className="stat-card-icon">{icon}</span>}
      <span className="stat-card-label">{label}</span>
      <span className="stat-card-value">{value}</span>
      {context && <span className="stat-card-context">{context}</span>}
      {onClick && (
        <button type="button" className="link-button" onClick={onClick} style={{ marginTop: "0.4rem", alignSelf: "flex-start" }}>
          {actionLabel || "View →"}
        </button>
      )}
    </div>
  );
}
