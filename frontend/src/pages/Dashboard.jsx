import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  detectConflicts,
  evaluateEligibility,
  generateChecklist,
  getCitizen,
  getScheme,
  getWebSchemes,
  listSavedSchemes,
  listSchemes,
  optimizeBundle,
} from "../api/client";
import AppShell from "../components/layout/AppShell";
import EmptyState from "../components/EmptyState";
import FilterPanel from "../components/FilterPanel";
import SchemeCard from "../components/SchemeCard";
import StatCard from "../components/StatCard";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { boolToTriState, toBoolOrUndefined } from "../lib/profileFields";
import { computeAge, evaluateSchemeAgainstFilters } from "../lib/ruleMatch";
import { clearStoredCitizenId, getStoredCitizenId, setStoredBundleId } from "../lib/storage";
import { humanizeReason } from "../lib/reasonText";

function filtersFromCitizen(citizen) {
  return {
    state: citizen.state || "",
    occupation: citizen.occupation || "",
    employment_status: citizen.employment_status || "",
    education_level: citizen.education_level || "",
    social_category: citizen.social_category || "",
    marital_status: citizen.marital_status || "",
    gender: citizen.gender || "",
    bpl_status: boolToTriState(citizen.bpl_status),
    disability_status: boolToTriState(citizen.disability_status),
    age: citizen.date_of_birth ? String(computeAge(citizen.date_of_birth)) : "",
    annual_income: citizen.annual_income != null ? String(citizen.annual_income) : "",
    land_holding_acres: citizen.land_holding_acres != null ? String(citizen.land_holding_acres) : "",
  };
}

function normalizeFilters(filters) {
  const num = (v) => (v !== "" && v != null ? Number(v) : undefined);
  return {
    state: filters.state || undefined,
    occupation: filters.occupation || undefined,
    employment_status: filters.employment_status || undefined,
    education_level: filters.education_level || undefined,
    social_category: filters.social_category || undefined,
    marital_status: filters.marital_status || undefined,
    gender: filters.gender || undefined,
    bpl_status: toBoolOrUndefined(filters.bpl_status),
    disability_status: toBoolOrUndefined(filters.disability_status),
    age: num(filters.age),
    annual_income: num(filters.annual_income),
    land_holding_acres: num(filters.land_holding_acres),
  };
}

const EMPTY_FILTERS = {
  state: "",
  occupation: "",
  employment_status: "",
  education_level: "",
  social_category: "",
  marital_status: "",
  gender: "",
  bpl_status: "",
  disability_status: "",
  age: "",
  annual_income: "",
  land_holding_acres: "",
};

const STATUS_RANK = { eligible: 0, indeterminate: 1, not_eligible: 2 };

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function Dashboard() {
  const navigate = useNavigate();
  const citizenId = getStoredCitizenId();

  const [citizen, setCitizen] = useState(null);
  const [citizenError, setCitizenError] = useState(null);

  const [personalized, setPersonalized] = useState({
    loading: true,
    error: null,
    bundle: null,
    schemes: [],
    eligibleCount: null,
    eligibilityResults: null,
    conflicts: null,
    missingDocsCount: null,
    checklistItems: [],
    analyzedAt: null,
  });

  const [allSchemes, setAllSchemes] = useState([]);
  const [schemesError, setSchemesError] = useState(null);

  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [profileDefaults, setProfileDefaults] = useState(EMPTY_FILTERS);
  const [searchText, setSearchText] = useState("");

  const [savedSchemeIds, setSavedSchemeIds] = useState(new Set());

  const [webSchemes, setWebSchemes] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    if (!citizenId) navigate("/", { replace: true });
  }, [citizenId, navigate]);

  useEffect(() => {
    if (!citizenId) return;
    listSavedSchemes(citizenId)
      .then((saved) => setSavedSchemeIds(new Set(saved.map((s) => s.scheme_id))))
      .catch(() => {});
  }, [citizenId]);

  const loadWebSchemes = useCallback(
    (force = false) => {
      if (!citizenId) return;
      setWebSchemes((prev) => ({ ...prev, loading: true, error: null }));
      getWebSchemes(citizenId, { force })
        .then((data) => setWebSchemes({ loading: false, error: null, data }))
        .catch((err) => setWebSchemes({ loading: false, error: err, data: null }));
    },
    [citizenId],
  );

  useEffect(() => {
    loadWebSchemes(false);
  }, [loadWebSchemes]);

  useEffect(() => {
    if (!citizenId) return;
    getCitizen(citizenId)
      .then((c) => {
        setCitizen(c);
        const defaults = filtersFromCitizen(c);
        setFilters(defaults);
        setProfileDefaults(defaults);
      })
      .catch((err) => setCitizenError(err));
  }, [citizenId]);

  const loadPersonalized = useCallback(() => {
    if (!citizenId) return undefined;
    let cancelled = false;
    setPersonalized((prev) => ({ ...prev, loading: true, error: null }));
    (async () => {
      try {
        const eligibility = await evaluateEligibility(citizenId);
        const eligibleCount = eligibility.results.filter((r) => r.status === "eligible").length;
        const conflictData = await detectConflicts(citizenId);
        const bundle = await optimizeBundle(citizenId);
        const schemes = await Promise.all(bundle.scheme_ids.map((id) => getScheme(id)));
        setStoredBundleId(bundle.bundle_id);
        let missingDocsCount = null;
        let checklistItems = [];
        if (bundle.bundle_id) {
          try {
            const checklist = await generateChecklist(bundle.bundle_id);
            checklistItems = checklist.checklist_items || [];
            missingDocsCount = checklistItems.filter((i) => i.status !== "held").length;
          } catch {
            missingDocsCount = null;
          }
        }
        if (!cancelled) {
          setPersonalized({
            loading: false,
            error: null,
            bundle,
            schemes,
            eligibleCount,
            eligibilityResults: eligibility.results,
            conflicts: conflictData.conflicts,
            missingDocsCount,
            checklistItems,
            analyzedAt: new Date(),
          });
        }
      } catch (err) {
        if (!cancelled) {
          setPersonalized({
            loading: false,
            error: err,
            bundle: null,
            schemes: [],
            eligibleCount: null,
            eligibilityResults: null,
            conflicts: null,
            missingDocsCount: null,
            checklistItems: [],
            analyzedAt: null,
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [citizenId]);

  useEffect(() => loadPersonalized(), [loadPersonalized]);

  useEffect(() => {
    listSchemes()
      .then(setAllSchemes)
      .catch((err) => setSchemesError(err));
  }, []);

  function handleFilterChange(e) {
    const { name, value } = e.target;
    setFilters((f) => ({ ...f, [name]: value }));
  }

  const hasFilterChanges = useMemo(
    () => JSON.stringify(filters) !== JSON.stringify(profileDefaults),
    [filters, profileDefaults],
  );

  const exploreResults = useMemo(() => {
    const normalized = normalizeFilters(filters);
    const q = searchText.trim().toLowerCase();
    return allSchemes
      .map((scheme) => {
        const { status, reasons } = evaluateSchemeAgainstFilters(scheme, normalized);
        return { scheme, status, reasons };
      })
      .filter(({ scheme }) => {
        if (!q) return true;
        const haystack = [scheme.name, scheme.description, scheme.category, scheme.issuing_authority]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(q);
      })
      .sort((a, b) => STATUS_RANK[a.status] - STATUS_RANK[b.status]);
  }, [allSchemes, filters, searchText]);

  const notEligibleCount = useMemo(
    () => (personalized.eligibilityResults || []).filter((r) => r.status === "not_eligible").length,
    [personalized.eligibilityResults],
  );

  const totalBenefit = useMemo(
    () => (personalized.schemes || []).reduce((sum, s) => sum + (s.benefit_value_estimate || 0), 0),
    [personalized.schemes],
  );

  const citationsBySchemeId = useMemo(() => {
    const map = new Map();
    (personalized.bundle?.policy_citations || []).forEach((c) => map.set(c.scheme_id, c));
    return map;
  }, [personalized.bundle]);

  const SUGGESTION_CHIPS = ["Schemes for farmers", "Housing schemes", "Education support", "Pension schemes", `Schemes in ${citizen?.state || "my state"}`];

  const nextActions = useMemo(() => {
    const actions = [];
    (personalized.eligibilityResults || [])
      .filter((r) => r.status === "indeterminate")
      .slice(0, 3)
      .forEach((r) => {
        actions.push({
          key: `elig-${r.scheme_id}`,
          title: `Complete details for ${r.scheme_name}`,
          description: r.reasons?.[0] ? humanizeReason(r.reasons[0]) : "One or more conditions still need more information.",
          priority: "medium",
          onClick: () => navigate("/profile"),
        });
      });
    if (personalized.missingDocsCount) {
      actions.push({
        key: "docs",
        title: `Upload ${personalized.missingDocsCount} missing document${personalized.missingDocsCount === 1 ? "" : "s"}`,
        description: "Needed to complete your application plan.",
        priority: "high",
        onClick: () =>
          personalized.bundle?.bundle_id &&
          navigate(`/bundles/${personalized.bundle.bundle_id}/checklist?citizen=${citizenId}`),
      });
    }
    return actions;
  }, [personalized, navigate, citizenId]);

  if (!citizenId) {
    return null;
  }

  if (citizenError) {
    return (
      <main className="page">
        <ErrorMessage error={citizenError}>We couldn&apos;t load your profile. It may no longer exist.</ErrorMessage>
        <button
          type="button"
          onClick={() => {
            clearStoredCitizenId();
            navigate("/");
          }}
        >
          Start over
        </button>
      </main>
    );
  }

  return (
    <AppShell
      active="overview"
      title={citizen ? `${greeting()}, ${citizen.name.split(" ")[0]}` : "Overview"}
      subtitle="Your personalized benefits overview is ready."
      meta={personalized.analyzedAt && `Last analyzed ${personalized.analyzedAt.toLocaleTimeString()}`}
      actions={
        <>
          <button type="button" className="ghost small" onClick={() => navigate("/profile")}>
            Edit profile
          </button>
        </>
      }
    >
      <section className="dashboard-section">
        <div className="dashboard-hero">
          <h1>{citizen ? `${greeting()}, ${citizen.name.split(" ")[0]}!` : greeting()}</h1>
          <p>Find government schemes that are right for you — ask, search, or explore in simple language.</p>
          <form
            className="dashboard-hero-search"
            onSubmit={(e) => {
              e.preventDefault();
              document.getElementById("explore-schemes")?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            <input
              type="search"
              className="search-input"
              placeholder='Ask about government schemes (e.g. "Schemes for farmers in Maharashtra")'
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              aria-label="Search schemes"
            />
            <button type="submit">Search</button>
          </form>
          <div className="dashboard-hero-chips">
            {SUGGESTION_CHIPS.map((chip) => (
              <button
                type="button"
                key={chip}
                className="chip-suggestion"
                onClick={() => {
                  setSearchText(chip);
                  document.getElementById("explore-schemes")?.scrollIntoView({ behavior: "smooth" });
                }}
              >
                {chip}
              </button>
            ))}
          </div>
        </div>

        {personalized.loading && <LoadingMessage>Evaluating your profile…</LoadingMessage>}

        {personalized.error && personalized.error.status === 409 && (
          <ErrorMessage onRetry={loadPersonalized}>
            None of our schemes could be evaluated with what you&apos;ve told us so far — add a few
            more details to your profile to get a match.
          </ErrorMessage>
        )}
        {personalized.error && personalized.error.status !== 409 && (
          <ErrorMessage error={personalized.error} onRetry={loadPersonalized} />
        )}

        {personalized.bundle && (
          <>
            <div className="stat-card-row">
              <StatCard
                icon="🗺️"
                tone="success"
                label="Potentially eligible"
                value={personalized.eligibleCount}
                context="Schemes matching your profile"
              />
              <StatCard
                icon="⏱️"
                tone="warning"
                label="Needs verification"
                value={(personalized.eligibilityResults || []).filter((r) => r.status === "indeterminate").length}
                context="Missing a detail or two"
              />
              <StatCard icon="✕" tone="danger" label="Not eligible" value={notEligibleCount} context="Doesn't match your profile" />
              <StatCard
                icon="🎁"
                tone="info"
                label="Total estimated benefit"
                value={`₹${totalBenefit.toLocaleString()}`}
                context="Across your selected bundle"
              />
            </div>

            <div className="dashboard-columns">
              <div className="dashboard-main-col">
                {nextActions.length > 0 && (
                  <div style={{ marginBottom: "1.75rem" }}>
                    <h2>Your next best actions</h2>
                    <div className="action-list">
                      {nextActions.map((action) => (
                        <div className="action-item" key={action.key}>
                          <span className={`action-item-priority ${action.priority === "high" ? "" : "low"}`} />
                          <div className="action-item-body">
                            <div>
                              <strong>{action.title}</strong>
                              <p>{action.description}</p>
                            </div>
                          </div>
                          <button type="button" className="secondary small" onClick={action.onClick}>
                            Act now
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {personalized.schemes.length === 0 && (
                  <EmptyState
                    icon="◇"
                    title="No viable bundle yet"
                    description="None of your eligible schemes could be included together — check the compatibility review for details."
                  />
                )}

                {personalized.schemes.length > 0 && (
                  <>
                    <h2>Recommended schemes for you</h2>
                    <div className="scheme-grid">
                      {personalized.schemes.slice(0, 4).map((s) => (
                        <SchemeCard
                          key={s.id}
                          scheme={s}
                          matchStatus="eligible"
                          citizenId={citizenId}
                          citation={citationsBySchemeId.get(s.id)}
                          initialSaved={savedSchemeIds.has(s.id)}
                          onSavedChange={(id, isSaved) =>
                            setSavedSchemeIds((prev) => {
                              const next = new Set(prev);
                              isSaved ? next.add(id) : next.delete(id);
                              return next;
                            })
                          }
                        />
                      ))}
                    </div>
                  </>
                )}

                <div className="actions">
                  <button type="button" className="ghost" onClick={() => navigate(`/citizens/${citizenId}/eligibility`)}>
                    View All →
                  </button>
                  <button type="button" className="ghost" onClick={() => navigate(`/citizens/${citizenId}/trace`)}>
                    Reasoning trace →
                  </button>
                  <button type="button" className="ghost" onClick={() => navigate("/saved-schemes")}>
                    Saved schemes →
                  </button>
                </div>

              </div>

              <aside className="right-rail">
                <div className="right-rail-card">
                  <h3>💎 Your Optimized Scheme Bundle</h3>
                  <div className="right-rail-bundle-stats">
                    <div>
                      <strong>{personalized.schemes.length}</strong>
                      <span>Schemes selected</span>
                    </div>
                    <div>
                      <strong>₹{totalBenefit.toLocaleString()}</strong>
                      <span>Total estimated benefit</span>
                    </div>
                  </div>
                  <p className="hint" style={{ marginBottom: "0.9rem" }}>
                    {personalized.conflicts?.length
                      ? `${personalized.conflicts.length} conflict(s) reviewed and resolved.`
                      : "Conflict-free — no overlapping or mutually exclusive schemes."}
                  </p>
                  <button
                    type="button"
                    style={{ width: "100%" }}
                    onClick={() =>
                      navigate(`/citizens/${citizenId}/bundle`, {
                        state: { bundle: personalized.bundle, schemes: personalized.schemes, conflicts: personalized.conflicts },
                      })
                    }
                  >
                    View Bundle Details →
                  </button>
                </div>

                <div className="right-rail-card">
                  <h3>📄 Missing Documents</h3>
                  {personalized.checklistItems.length === 0 && (
                    <p className="hint">Nothing to check yet — your bundle has no document requirements loaded.</p>
                  )}
                  <div className="right-rail-checklist">
                    {personalized.checklistItems.slice(0, 6).map((item) => (
                      <div className="right-rail-checklist-item" key={item.document_type}>
                        <span>{item.document_type}</span>
                        <span className={`doc-status ${item.status === "held" ? "doc-status-held" : "doc-status-missing"}`}>
                          {item.status === "held" ? "Available" : "Not provided"}
                        </span>
                      </div>
                    ))}
                  </div>
                  {personalized.bundle.bundle_id && (
                    <button
                      type="button"
                      className="secondary"
                      style={{ width: "100%" }}
                      onClick={() => navigate(`/bundles/${personalized.bundle.bundle_id}/checklist?citizen=${citizenId}`)}
                    >
                      View Checklist →
                    </button>
                  )}
                </div>

                <div className="ai-assistant-card">
                  <h3>💬 Need Help?</h3>
                  <p>Get simple explanations, document guidance, and help with application forms in English, Hindi, or Marathi.</p>
                  <button type="button" onClick={() => navigate("/converse")}>
                    Start Chat →
                  </button>
                </div>
              </aside>
            </div>
          </>
        )}

        <div style={{ marginTop: "1.75rem" }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "0.75rem" }}>
            <h2>More schemes found on the web</h2>
            <button
              type="button"
              className="ghost small"
              onClick={() => loadWebSchemes(true)}
              disabled={webSchemes.loading}
            >
              {webSchemes.loading ? "Searching…" : "Refresh"}
            </button>
          </div>
          <p className="hint">
            Not part of our curated catalogue — found via public web search and not independently
            verified. Confirm any details on the scheme&apos;s own official page before relying on them.
          </p>

          {webSchemes.loading && !webSchemes.data && <LoadingMessage>Searching the web…</LoadingMessage>}
          {webSchemes.error && <InfoMessage>Couldn&apos;t search the web for more schemes right now.</InfoMessage>}
          {webSchemes.data && webSchemes.data.suggestions.length === 0 && (
            <InfoMessage>No additional schemes found on the web right now.</InfoMessage>
          )}
          {webSchemes.data && webSchemes.data.suggestions.length > 0 && (
            <div className="scheme-grid">
              {webSchemes.data.suggestions.map((s, i) => (
                <article className="scheme-card" key={`${s.name}-${i}`}>
                  <div className="scheme-card-top">
                    <span className="chip chip-tag">Unverified · from the web</span>
                  </div>
                  <h3>{s.name}</h3>
                  {s.issuing_authority && <p className="scheme-card-authority">{s.issuing_authority}</p>}
                  {s.description && <p className="scheme-card-desc">{s.description}</p>}
                  {s.links?.source_url && (
                    <a href={s.links.source_url} target="_blank" rel="noreferrer">
                      Source ↗
                    </a>
                  )}
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="dashboard-section" id="explore-schemes">
        <div className="page-header">
          <h2>Explore all schemes</h2>
          <p>Search the full catalogue, or try different filter values to check eligibility for someone else.</p>
        </div>

        <div className="explore-controls">
          <input
            type="search"
            className="search-input"
            placeholder="Search schemes by name, category, or department…"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            aria-label="Search schemes"
          />
          <FilterPanel
            filters={filters}
            onFieldChange={handleFilterChange}
            onReset={() => setFilters(profileDefaults)}
            onClear={() => setFilters(EMPTY_FILTERS)}
            hasChanges={hasFilterChanges}
          />
        </div>

        {schemesError && <ErrorMessage error={schemesError} />}

        {allSchemes.length === 0 && !schemesError && <LoadingMessage>Loading scheme catalogue…</LoadingMessage>}

        {exploreResults.length > 0 && (
          <div className="scheme-grid">
            {exploreResults.map(({ scheme, status, reasons }) => (
              <SchemeCard
                key={scheme.id}
                scheme={scheme}
                matchStatus={status}
                reasons={reasons}
                citizenId={citizenId}
                initialSaved={savedSchemeIds.has(scheme.id)}
                onSavedChange={(id, isSaved) =>
                  setSavedSchemeIds((prev) => {
                    const next = new Set(prev);
                    isSaved ? next.add(id) : next.delete(id);
                    return next;
                  })
                }
              />
            ))}
          </div>
        )}

        {allSchemes.length > 0 && exploreResults.length === 0 && (
          <InfoMessage>No schemes match your search.</InfoMessage>
        )}
      </section>
    </AppShell>
  );
}
