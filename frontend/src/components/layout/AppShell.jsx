import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { clearSession } from "../../auth/session";
import NotificationBell from "../NotificationBell";
import HelpDrawer from "../HelpDrawer";
import { clearStoredCitizenId, getStoredBundleId, getStoredCitizenId } from "../../lib/storage";

const PRIMARY_NAV = [
  { key: "overview", label: "Dashboard", icon: "⌂", path: () => "/dashboard" },
  { key: "catalog", label: "Explore Schemes", icon: "🔍", path: () => "/catalog" },
  {
    key: "eligibility",
    label: "Eligible Schemes",
    icon: "✓",
    path: ({ citizenId }) => citizenId && `/citizens/${citizenId}/eligibility`,
  },
  {
    key: "bundle",
    label: "My Applications",
    icon: "◆",
    path: ({ citizenId }) => citizenId && `/citizens/${citizenId}/bundle`,
  },
  {
    key: "checklist",
    label: "Documents",
    icon: "☰",
    path: ({ citizenId, bundleId }) => citizenId && bundleId && `/bundles/${bundleId}/checklist?citizen=${citizenId}`,
  },
  { key: "assistant", label: "AI Assistant", icon: "💬", path: () => "/converse" },
  { key: "profile", label: "Settings", icon: "◔", path: () => "/profile" },
];

const SECONDARY_NAV = [
  { key: "saved", label: "Saved Schemes", icon: "★", path: () => "/saved-schemes" },
  { key: "activity", label: "Activity", icon: "◷", path: () => "/activity" },
  { key: "grievances", label: "Help & Support", icon: "◎", path: () => "/grievances" },
];

const ADMIN_NAV = [
  { key: "admin-schemes", label: "Scheme Catalog", icon: "⌂", path: () => "/admin" },
  { key: "admin-rag", label: "RAG Candidates", icon: "🔍", path: () => "/admin/rag-candidates" },
  { key: "admin-grievances", label: "Grievances", icon: "◎", path: () => "/admin/grievances" },
  { key: "admin-fraud", label: "Fraud Review", icon: "✕", path: () => "/admin/fraud" },
  { key: "admin-analytics", label: "Analytics", icon: "◆", path: () => "/admin/analytics" },
  { key: "admin-reports", label: "Scheme Reports", icon: "☰", path: () => "/admin/scheme-reports" },
];

function SidebarNav({ active, citizenId, bundleId, onNavigate, variant }) {
  const items = variant === "admin" ? ADMIN_NAV : PRIMARY_NAV;
  return (
    <>
      <div className="app-sidebar-brand">
        🌱 ASBO
        <span className="app-sidebar-tagline">{variant === "admin" ? "Admin Console" : "Connecting Citizens to Opportunities"}</span>
      </div>
      <nav className="app-sidebar-nav" aria-label="Main navigation">
        {items.map((item) => {
          const path = item.path({ citizenId, bundleId });
          const isActive = item.key === active;
          if (!path) {
            return (
              <span key={item.key} className="app-sidebar-link disabled">
                <span className="app-sidebar-icon">{item.icon}</span>
                {item.label}
              </span>
            );
          }
          return (
            <Link
              key={item.key}
              to={path}
              className={`app-sidebar-link${isActive ? " active" : ""}`}
              onClick={onNavigate}
            >
              <span className="app-sidebar-icon">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
        {variant !== "admin" && <div className="app-sidebar-section-label">More</div>}
        {variant !== "admin" && SECONDARY_NAV.map((item) => (
          <Link key={item.key} to={item.path()} className="app-sidebar-link" onClick={onNavigate}>
            <span className="app-sidebar-icon">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
    </>
  );
}

// Shared authenticated-citizen layout: compact sidebar (nav mirrors the PS16 workflow order),
// a topbar carrying the page title/subtitle/meta, and the floating "Ask Sahayak" help drawer.
// Rendered per-page (not a router layout route) so each page keeps full control of its own
// data-fetching — this only changes presentation.
export default function AppShell({ active, title, subtitle, meta, actions, children, variant = "citizen" }) {
  const navigate = useNavigate();
  const citizenId = getStoredCitizenId();
  const bundleId = getStoredBundleId();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-shell">
      <div className="mobile-topbar">
        <span className="mobile-topbar-brand">ASBO</span>
        <button type="button" className="mobile-menu-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
          ☰ Menu
        </button>
      </div>

      <div className={`app-sidebar-backdrop${mobileOpen ? " open" : ""}`} onClick={() => setMobileOpen(false)} />
      <aside className={`app-sidebar${mobileOpen ? " open" : ""}`}>
        <SidebarNav active={active} citizenId={citizenId} bundleId={bundleId} onNavigate={() => setMobileOpen(false)} variant={variant} />
        <div className="app-sidebar-footer">
          <button
            type="button"
            className="app-sidebar-link"
            style={{ width: "100%", border: "none", background: "none", cursor: "pointer" }}
            onClick={() => {
              if (variant === "admin") {
                clearSession();
                navigate("/login");
              } else {
                clearStoredCitizenId();
                navigate("/");
              }
            }}
          >
            <span className="app-sidebar-icon">⇤</span>
            {variant === "admin" ? "Log out" : "Switch profile"}
          </button>
        </div>
      </aside>

      <div className="app-shell-body">
        <header className="app-topbar">
          <div className="app-topbar-title">
            <h1>{title}</h1>
            {subtitle && <p>{subtitle}</p>}
            {meta && <div className="app-topbar-meta">{meta}</div>}
          </div>
          <div className="app-topbar-actions">
            {actions}
            <NotificationBell citizenId={citizenId} />
          </div>
        </header>
        <main className="app-main">{children}</main>
      </div>

      <HelpDrawer />
    </div>
  );
}
