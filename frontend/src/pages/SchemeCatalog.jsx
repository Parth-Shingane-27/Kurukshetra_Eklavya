import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSchemeGuide, getVideoTutorial, searchCatalog, searchCatalogNaturalLanguage } from "../api/client";
import AppShell from "../components/layout/AppShell";
import ApplyLink from "../components/ApplyLink";
import ReportSchemeControl from "../components/ReportSchemeControl";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";

// FR-014 — searchable scheme catalog with form-filling guides. Public, no login, no citizen
// profile involved — independent of any personal eligibility check (Section 13a).
export default function SchemeCatalog() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [schemes, setSchemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [nlText, setNlText] = useState("");
  const [nlLoading, setNlLoading] = useState(false);
  const [nlError, setNlError] = useState(null);
  const [nlInterpretation, setNlInterpretation] = useState(null);

  const [expandedId, setExpandedId] = useState(null);
  const [guidesById, setGuidesById] = useState({});
  const [guideLoadingId, setGuideLoadingId] = useState(null);
  const [guideError, setGuideError] = useState(null);
  const [lang, setLang] = useState("en");

  const [videoById, setVideoById] = useState({});
  const [videoLoadingId, setVideoLoadingId] = useState(null);

  useEffect(() => {
    runSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runSearch(e) {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    setNlInterpretation(null);
    try {
      const results = await searchCatalog({ query: query.trim() || undefined, category: category || undefined });
      setSchemes(results);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  async function runNaturalLanguageSearch(e) {
    e.preventDefault();
    if (!nlText.trim()) return;
    setNlLoading(true);
    setNlError(null);
    try {
      const result = await searchCatalogNaturalLanguage(nlText.trim());
      setSchemes(result.schemes);
      setNlInterpretation(result);
      setQuery("");
      setCategory("");
    } catch (err) {
      setNlError(err);
    } finally {
      setNlLoading(false);
    }
  }

  async function toggleGuide(scheme) {
    if (expandedId === scheme.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(scheme.id);
    setGuideError(null);

    if (!guidesById[scheme.id]) {
      setGuideLoadingId(scheme.id);
      getSchemeGuide(scheme.id)
        .then((data) => setGuidesById((prev) => ({ ...prev, [scheme.id]: data })))
        .catch((err) => setGuideError(err))
        .finally(() => setGuideLoadingId(null));
    }

    // Independent of the guide fetch above — a slow/unavailable video recommendation must
    // never delay or break the step-by-step Form Guide itself.
    if (!videoById[scheme.id]) {
      setVideoLoadingId(scheme.id);
      getVideoTutorial(scheme.id)
        .then((data) => setVideoById((prev) => ({ ...prev, [scheme.id]: data })))
        .catch(() => setVideoById((prev) => ({ ...prev, [scheme.id]: { available: false, reason: "Video tutorial unavailable." } })))
        .finally(() => setVideoLoadingId((current) => (current === scheme.id ? null : current)));
    }
  }

  const categories = [...new Set(schemes.map((s) => s.category))].sort();

  return (
    <AppShell
      active="catalog"
      title="Scheme catalog"
      subtitle="Browse and search every active scheme — no account or profile needed."
      meta={<Link to="/national-search">Search the wider national scheme database →</Link>}
    >
      <form className="card catalog-search" onSubmit={runNaturalLanguageSearch}>
        <label>
          Describe what you need, in your own words
          <input
            type="text"
            placeholder="e.g. I'm a farmer looking for income support in Maharashtra"
            value={nlText}
            onChange={(e) => setNlText(e.target.value)}
          />
        </label>
        <div className="actions">
          <button type="submit" disabled={nlLoading || !nlText.trim()}>
            {nlLoading ? "Understanding your request…" : "Search"}
          </button>
        </div>
        {nlError && <ErrorMessage error={nlError} />}
        {nlInterpretation && (
          <InfoMessage>
            {nlInterpretation.used_ai
              ? `Searched for "${nlInterpretation.interpreted_topic}"${nlInterpretation.interpreted_state ? ` in ${nlInterpretation.interpreted_state}` : ""}.`
              : "Couldn't interpret that automatically — searched using your exact words instead."}
          </InfoMessage>
        )}
      </form>

      <form className="card catalog-search" onSubmit={runSearch}>
        <div className="form-grid">
          <label>
            Search
            <input
              type="text"
              placeholder="Scheme name, category, or keyword…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <label>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="actions">
          <button type="submit" disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
      </form>

      {loading && <LoadingMessage>Loading catalog…</LoadingMessage>}
      {error && <ErrorMessage error={error} />}
      {!loading && !error && schemes.length === 0 && (
        <InfoMessage>No schemes matched your search.</InfoMessage>
      )}

      <div className="catalog-list">
        {schemes.map((scheme) => (
          <div className="card catalog-item" key={scheme.id}>
            <div className="scheme-row">
              <div>
                <strong>{scheme.name}</strong>
                <p className="hint">{scheme.category}</p>
                {scheme.description && <p>{scheme.description}</p>}
              </div>
              <button type="button" className="secondary" onClick={() => toggleGuide(scheme)}>
                {expandedId === scheme.id ? "Hide details" : "View guide"}
              </button>
            </div>

            {/* Always visible, regardless of whether the guide is expanded — a citizen just
                browsing the catalog should never have to expand the guide first to apply. */}
            <ApplyLink
              url={scheme.links?.application_url}
              status={scheme.links?.application_link_status}
              moreInfoUrl={scheme.links?.official_scheme_url}
              schemeId={scheme.id}
            />

            {expandedId === scheme.id && (
              <div className="catalog-guide">
                {guideLoadingId === scheme.id && <LoadingMessage>Loading guide…</LoadingMessage>}
                {guideError && <ErrorMessage error={guideError} />}
                {guidesById[scheme.id] && (
                  <>
                    {guidesById[scheme.id].guide ? (
                      <>
                        <div className="lang-toggle">
                          <button
                            type="button"
                            className={lang === "en" ? "secondary active" : "secondary"}
                            onClick={() => setLang("en")}
                          >
                            English
                          </button>
                          <button
                            type="button"
                            className={lang === "mr" ? "secondary active" : "secondary"}
                            onClick={() => setLang("mr")}
                          >
                            मराठी
                          </button>
                        </div>
                        <ol className="guide-steps">
                          {(lang === "mr"
                            ? guidesById[scheme.id].guide.guide_mr
                            : guidesById[scheme.id].guide.guide_en
                          ).map((step, i) => (
                            <li key={i}>{step}</li>
                          ))}
                        </ol>
                        {guidesById[scheme.id].guide.video_url && (
                          <a href={guidesById[scheme.id].guide.video_url} target="_blank" rel="noreferrer">
                            Watch video walkthrough ↗
                          </a>
                        )}
                      </>
                    ) : (
                      <InfoMessage>
                        A step-by-step form-filling guide hasn&apos;t been written for this scheme yet — use
                        the application link above and the official scheme page for now.
                      </InfoMessage>
                    )}
                  </>
                )}

                {/* Shown for every expanded scheme's policy/form information — not only ones
                    with an authored step-by-step guide — since the video recommendation is
                    keyed off the scheme's own name/category, not the guide's presence. */}
                <div className="video-tutorial-option">
                  <p className="hint">— OR —</p>
                  {videoLoadingId === scheme.id && !videoById[scheme.id] && (
                    <p className="hint">Finding the best video tutorial…</p>
                  )}
                  {videoById[scheme.id]?.available && (
                    <a
                      className="watch-video-button"
                      href={videoById[scheme.id].youtube_url}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`Watch YouTube tutorial for filling the ${scheme.name} form: ${videoById[scheme.id].title}`}
                    >
                      📺 Watch Video Tutorial
                    </a>
                  )}
                  {videoById[scheme.id] && !videoById[scheme.id].available && (
                    <p className="hint">{videoById[scheme.id].reason || "Video tutorial unavailable."}</p>
                  )}
                </div>

                <ReportSchemeControl schemeId={scheme.id} />
              </div>
            )}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
