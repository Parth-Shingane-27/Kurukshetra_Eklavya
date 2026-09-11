import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCitizen } from "../api/client";
import { getStoredCitizenId, setStoredCitizenId } from "../lib/storage";

export default function Landing() {
  const navigate = useNavigate();
  const [checkingSession, setCheckingSession] = useState(true);
  const [resumeId, setResumeId] = useState("");
  const [resumeError, setResumeError] = useState(null);
  const [resuming, setResuming] = useState(false);

  useEffect(() => {
    const storedId = getStoredCitizenId();
    if (!storedId) {
      setCheckingSession(false);
      return;
    }
    let cancelled = false;
    getCitizen(storedId)
      .then(() => {
        if (!cancelled) navigate("/dashboard", { replace: true });
      })
      .catch(() => {
        if (!cancelled) setCheckingSession(false);
      });
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  async function handleResume(e) {
    e.preventDefault();
    const id = resumeId.trim();
    if (!id) return;
    setResuming(true);
    setResumeError(null);
    try {
      await getCitizen(id);
      setStoredCitizenId(id);
      navigate("/dashboard");
    } catch {
      setResumeError("We couldn't find a profile with that ID. Check it and try again.");
    } finally {
      setResuming(false);
    }
  }

  if (checkingSession) {
    return (
      <main className="page hero-page">
        <span className="spinner" aria-hidden="true" />
      </main>
    );
  }

  return (
    <main className="page hero-page">
      <div className="hero">
        <span className="eyebrow">Citizen Benefits Assistant</span>
        <h1>Find every scheme you qualify for — in under a minute.</h1>
        <p className="hero-sub">
          Answer a few quick questions once. We&apos;ll match you against every active government
          scheme, resolve conflicts automatically, and hand you a ready-to-use application
          checklist.
        </p>
        <div className="hero-actions">
          <button type="button" onClick={() => navigate("/onboarding")}>
            Get started
          </button>
        </div>

        <details className="resume-disclosure">
          <summary>Already have a profile?</summary>
          <form className="resume-form" onSubmit={handleResume}>
            <input
              type="text"
              placeholder="Paste your profile ID"
              value={resumeId}
              onChange={(e) => setResumeId(e.target.value)}
              aria-label="Profile ID"
            />
            <button type="submit" className="secondary" disabled={resuming}>
              {resuming ? "Checking…" : "Resume"}
            </button>
          </form>
          {resumeError && (
            <p className="field-error" role="alert">
              {resumeError}
            </p>
          )}
        </details>
      </div>

      <div className="hero-steps">
        <div className="hero-step">
          <span className="hero-step-number">1</span>
          <div>
            <strong>Tell us about yourself</strong>
            <p>A short, skippable form — only four fields are required.</p>
          </div>
        </div>
        <div className="hero-step">
          <span className="hero-step-number">2</span>
          <div>
            <strong>Get your personalized dashboard</strong>
            <p>See eligible schemes, an optimized bundle, and what to do next.</p>
          </div>
        </div>
        <div className="hero-step">
          <span className="hero-step-number">3</span>
          <div>
            <strong>Explore beyond your own profile</strong>
            <p>Filter and search the full scheme catalogue for family or research.</p>
          </div>
        </div>
      </div>
    </main>
  );
}
