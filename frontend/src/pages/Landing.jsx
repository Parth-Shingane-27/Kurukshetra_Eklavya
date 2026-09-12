import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCitizen } from "../api/client";
import { getUser, isLoggedIn } from "../auth/session";
import { clearStoredCitizenId, setStoredCitizenId } from "../lib/storage";

const TRUST_ITEMS = [
  { title: "Profile-based", body: "Recommendations are based only on the details you give us — nothing assumed." },
  { title: "Transparent reasoning", body: "Every eligibility result comes with the plain-language reason behind it." },
  { title: "Compatibility-aware", body: "We check which schemes can actually be held together before recommending them." },
  { title: "Built for citizens", body: "Short forms, plain language, and a checklist you can act on immediately." },
];

const HOW_IT_WORKS = [
  { title: "Build your profile", body: "A short, skippable form — only four fields are required to start." },
  { title: "Discover relevant schemes", body: "We match you against every active scheme in the knowledge base." },
  { title: "Review compatibility", body: "See which combinations conflict and which work well together." },
  { title: "Follow your application plan", body: "A consolidated, document-aware checklist for everything you selected." },
];

const WHY_IT_MATTERS = [
  { title: "One profile instead of repeated searching", body: "Answer once, get matched everywhere — no re-entering the same details per scheme." },
  { title: "Clearer eligibility", body: "Understand exactly why a scheme applies to you, or what's still missing." },
  { title: "Visibility into missing documents", body: "See what you still need before you're midway through an application." },
  { title: "Organized application preparation", body: "One checklist, grouped by scheme, instead of scattered notes." },
];

export default function Landing() {
  const navigate = useNavigate();
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) {
      clearStoredCitizenId();
      setCheckingSession(false);
      return;
    }
    const citizenId = getUser()?.citizen_id;
    if (!citizenId) {
      setCheckingSession(false);
      return;
    }
    let cancelled = false;
    getCitizen(citizenId)
      .then(() => {
        if (!cancelled) {
          setStoredCitizenId(citizenId);
          navigate("/dashboard", { replace: true });
        }
      })
      .catch(() => {
        if (!cancelled) setCheckingSession(false);
      });
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  if (checkingSession) {
    return (
      <main className="page hero-page">
        <span className="spinner" aria-hidden="true" />
      </main>
    );
  }

  return (
    <main className="page hero-page">
      <div className="hero-split">
        <div className="hero">
          <span className="eyebrow">Citizen Benefits Intelligence</span>
          <h1>Understand your benefits. Plan your next steps.</h1>
          <p className="hero-sub">
            Discover potentially eligible government schemes, understand compatibility, and
            receive a personalized application plan — all from one citizen profile.
          </p>
          <div className="hero-actions">
            <button type="button" onClick={() => navigate("/onboarding")}>
              Check My Eligibility
            </button>
            <button type="button" className="secondary" onClick={() => navigate("/converse")}>
              See How It Works
            </button>
          </div>
          <div className="hero-actions">
            <button type="button" className="ghost" onClick={() => navigate("/quick-check")}>
              Quick check for one scheme →
            </button>
            <button type="button" className="ghost" onClick={() => navigate("/catalog")}>
              Browse the scheme catalog →
            </button>
          </div>

          <p className="hint" style={{ marginTop: "1rem" }}>
            Already have an account? <a href="#" onClick={(e) => { e.preventDefault(); navigate("/login"); }}>Log in</a> to
            see your personalized dashboard.
          </p>
        </div>

        <div className="hero-preview" aria-hidden="true">
          <div className="hero-preview-header">
            <span className="brand">ASBO</span>
            <span className="hero-preview-dot" />
          </div>
          <div className="hero-preview-profile">
            <span className="hero-preview-avatar">A</span>
            <div>
              <strong style={{ display: "block", fontSize: "0.92rem" }}>Citizen profile</strong>
              <span className="hint">Maharashtra · Farmer · BPL</span>
            </div>
          </div>
          <div className="hero-preview-mini-cards">
            <div className="hero-preview-mini-card">
              <strong>PM-KISAN</strong>
              <span className="badge badge-eligible">Eligible</span>
            </div>
            <div className="hero-preview-mini-card">
              <strong>Post-Matric Scholarship</strong>
              <span className="badge badge-indeterminate">Needs info</span>
            </div>
            <div className="hero-preview-mini-card">
              <strong>Housing Assistance</strong>
              <span className="badge badge-eligible">Eligible</span>
            </div>
          </div>
          <div className="hero-preview-bundle">
            <div>
              <strong>Optimized bundle</strong>
              <br />
              <span>3 schemes · 0 conflicts</span>
            </div>
            <span aria-hidden="true">→</span>
          </div>
        </div>
      </div>

      <div className="trust-strip">
        {TRUST_ITEMS.map((item) => (
          <div className="trust-item" key={item.title}>
            <strong>{item.title}</strong>
            {item.body}
          </div>
        ))}
      </div>

      <section className="landing-section">
        <div className="section-heading">
          <span className="eyebrow">How it works</span>
          <h2>Four steps from profile to application</h2>
        </div>
        <div className="hero-steps">
          {HOW_IT_WORKS.map((step, i) => (
            <div className="hero-step" key={step.title}>
              <span className="hero-step-number">{i + 1}</span>
              <div>
                <strong>{step.title}</strong>
                <p>{step.body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section">
        <div className="section-heading">
          <span className="eyebrow">Why it matters</span>
          <h2>Less searching, clearer decisions</h2>
        </div>
        <div className="why-grid">
          {WHY_IT_MATTERS.map((item) => (
            <div className="why-item" key={item.title}>
              <strong style={{ display: "block", color: "var(--text)", marginBottom: "0.3rem" }}>{item.title}</strong>
              <p style={{ margin: 0 }}>{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="landing-footer">
        <div>
          <span className="brand">ASBO</span>
          <p style={{ margin: "0.3rem 0 0", maxWidth: "40ch" }}>
            An autonomous scheme-bundle optimizer that helps citizens understand and access the
            support available to them.
          </p>
        </div>
        <nav>
          <a href="#" onClick={(e) => { e.preventDefault(); navigate("/catalog"); }}>Scheme catalog</a>
          <a href="#" onClick={(e) => { e.preventDefault(); navigate("/grievances"); }}>Help &amp; support</a>
          <a href="#" onClick={(e) => e.preventDefault()}>Privacy</a>
          <a href="#" onClick={(e) => e.preventDefault()}>Accessibility</a>
        </nav>
      </footer>
    </main>
  );
}
