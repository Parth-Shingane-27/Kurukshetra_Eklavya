// Lightweight page header for standalone pages (Landing, Onboarding) that don't run inside
// AppShell. Pages inside AppShell get their title/subtitle from AppShell's topbar instead.
export default function PageHeader({ eyebrow, title, subtitle, actions }) {
  return (
    <div className="page-header section-heading">
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
      {actions && <div className="actions">{actions}</div>}
    </div>
  );
}
