export default function EmptyState({ icon = "○", title, description, actionLabel, onAction }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon" aria-hidden="true">
        {icon}
      </div>
      <strong>{title}</strong>
      {description && <p>{description}</p>}
      {actionLabel && onAction && (
        <button type="button" className="secondary" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
