import { useState } from "react";
import { searchNationalSchemeDatabase } from "../api/client";
import AppShell from "../components/layout/AppShell";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";

const SECTION_LABELS = {
  details: "Overview",
  eligibility: "Eligibility",
  benefits: "Benefits",
  application: "How to apply",
  documents: "Documents required",
  structured_rule: "Structured rule",
};

// Searches the broader, RAG-indexed national scheme dataset (thousands of real government
// schemes) — distinct from the ~13-scheme curated catalogue (SchemeCatalog.jsx) that backs
// eligibility/bundle/checklist. Every result is honestly labeled by source: "curated_knowledge_base"
// only for schemes also present in our own curated catalogue, "dataset_provided" for everything
// else — never presented as independently verified, matching this app's existing honesty rule
// (app/rag/policy_service.py's module docstring).
export default function NationalSchemeSearch() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchNationalSchemeDatabase(query.trim());
      setResult(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell
      active="catalog"
      title="Search the national scheme database"
      subtitle="Search across thousands of real central and state government schemes. This is a wider, less-curated dataset than our main scheme catalogue — useful for research or discovery, but treat results as a starting point, not an official determination."
    >
      <form className="card catalog-search" onSubmit={handleSearch}>
        <label>
          What are you looking for?
          <input
            type="text"
            placeholder="e.g. fishermen relief assistance, widow pension Odisha, student scholarship SC/ST"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <div className="actions">
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
      </form>

      {loading && <LoadingMessage>Searching the national database…</LoadingMessage>}
      {error && <ErrorMessage error={error} />}

      {result && !result.verified && (
        <InfoMessage>{result.note || "Nothing could be retrieved for this search."}</InfoMessage>
      )}

      {result?.verified && (
        <div className="catalog-list">
          {result.evidence.map((e, i) => (
            <div className="card catalog-item" key={i}>
              <div className="scheme-row">
                <div>
                  <strong>{e.scheme_name}</strong>
                  <p className="hint">
                    {SECTION_LABELS[e.section] || e.section}
                    {" · "}
                    {e.source === "curated_knowledge_base" ? (
                      <span className="chip chip-tag">In our curated catalogue</span>
                    ) : (
                      "From the broader national dataset — not independently verified"
                    )}
                  </p>
                </div>
              </div>
              <p>{e.content}</p>
              {e.source_url && (
                <a href={e.source_url} target="_blank" rel="noreferrer">
                  Source ↗
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
