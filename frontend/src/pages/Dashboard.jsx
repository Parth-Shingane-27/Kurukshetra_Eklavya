import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { detectConflicts, evaluateEligibility, getCitizen, getScheme, listSchemes, optimizeBundle } from "../api/client";
import FilterPanel from "../components/FilterPanel";
import SchemeCard from "../components/SchemeCard";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { boolToTriState, toBoolOrUndefined } from "../lib/profileFields";
import { computeAge, evaluateSchemeAgainstFilters } from "../lib/ruleMatch";
import { clearStoredCitizenId, getStoredCitizenId } from "../lib/storage";

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

export default function Dashboard() {
  const navigate = useNavigate();
  const citizenId = getStoredCitizenId();

  const [citizen, setCitizen] = useState(null);
  const [citizenError, setCitizenError] = useState(null);

  const [personalized, setPersonalized] = useState({ loading: true, error: null, bundle: null, schemes: [], eligibleCount: null });

  const [allSchemes, setAllSchemes] = useState([]);
  const [schemesError, setSchemesError] = useState(null);

  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [profileDefaults, setProfileDefaults] = useState(EMPTY_FILTERS);
  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    if (!citizenId) navigate("/", { replace: true });
  }, [citizenId, navigate]);

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
    setPersonalized({ loading: true, error: null, bundle: null, schemes: [], eligibleCount: null });
    (async () => {
      try {
        const eligibility = await evaluateEligibility(citizenId);
        const eligibleCount = eligibility.results.filter((r) => r.status === "eligible").length;
        await detectConflicts(citizenId);
        const bundle = await optimizeBundle(citizenId);
        const schemes = await Promise.all(bundle.scheme_ids.map((id) => getScheme(id)));
        if (!cancelled) setPersonalized({ loading: false, error: null, bundle, schemes, eligibleCount });
      } catch (err) {
        if (!cancelled) setPersonalized({ loading: false, error: err, bundle: null, schemes: [], eligibleCount: null });
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
    <>
      <header className="dashboard-topbar">
        <span className="brand">ASBO</span>
        <div className="dashboard-topbar-actions">
          {citizen && <span className="dashboard-greeting">Hi, {citizen.name.split(" ")[0]}</span>}
          <button
            type="button"
            className="ghost small"
            onClick={() => {
              clearStoredCitizenId();
              navigate("/");
            }}
          >
            Switch profile
          </button>
        </div>
      </header>

      <main className="page dashboard-page">
        <section className="dashboard-section">
          <div className="page-header">
            <h1>Your recommended bundle</h1>
            <p>Based on the profile you gave us — updates automatically as schemes change.</p>
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
              <div className="stat-tiles">
                <div className="stat-tile">
                  <span className="stat-value">{personalized.eligibleCount}</span>
                  <span className="stat-label">Eligible schemes</span>
                </div>
                <div className="stat-tile">
                  <span className="stat-value">₹{personalized.bundle.total_benefit_value.toLocaleString()}</span>
                  <span className="stat-label">Optimized bundle value</span>
                </div>
                <div className="stat-tile">
                  <span className="stat-value">{personalized.bundle.excluded.length}</span>
                  <span className="stat-label">Excluded (conflicts)</span>
                </div>
              </div>

              {personalized.schemes.length === 0 && (
                <InfoMessage>No viable bundle yet — none of your eligible schemes could be included.</InfoMessage>
              )}

              {personalized.schemes.length > 0 && (
                <div className="scheme-grid">
                  {personalized.schemes.map((s) => (
                    <SchemeCard key={s.id} scheme={s} matchStatus="eligible" />
                  ))}
                </div>
              )}

              <div className="actions">
                <button type="button" className="secondary" onClick={() => navigate(`/citizens/${citizenId}/eligibility`)}>
                  Full eligibility breakdown →
                </button>
                <button type="button" className="secondary" onClick={() => navigate(`/citizens/${citizenId}/bundle`)}>
                  Bundle &amp; conflicts →
                </button>
                {personalized.bundle.bundle_id && (
                  <button
                    type="button"
                    onClick={() => navigate(`/bundles/${personalized.bundle.bundle_id}/checklist?citizen=${citizenId}`)}
                  >
                    Application checklist →
                  </button>
                )}
                <button type="button" className="ghost" onClick={() => navigate(`/citizens/${citizenId}/trace`)}>
                  Reasoning trace →
                </button>
              </div>
            </>
          )}
        </section>

        <section className="dashboard-section">
          <div className="page-header">
            <h1>Explore all schemes</h1>
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
                <SchemeCard key={scheme.id} scheme={scheme} matchStatus={status} reasons={reasons} />
              ))}
            </div>
          )}

          {allSchemes.length > 0 && exploreResults.length === 0 && (
            <InfoMessage>No schemes match your search.</InfoMessage>
          )}
        </section>
      </main>
    </>
  );
}
