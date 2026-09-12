import { useEffect, useState } from "react";
import { getScheme, listSchemes, quickCheck } from "../api/client";
import AppShell from "../components/layout/AppShell";
import ApplyLink from "../components/ApplyLink";
import { SelectField, TextField } from "../components/FormField";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import StatusBadge from "../components/StatusBadge";
import { buildCriteria, fieldsForRules } from "../lib/quickCheckFields";
import { humanizeReason } from "../lib/reasonText";

// FR-013 — no account, no login, no citizen record created (BR-014). Anyone can check
// eligibility for themselves or on behalf of someone else, for exactly one scheme at a time.
export default function QuickChecker() {
  const [schemes, setSchemes] = useState([]);
  const [schemesError, setSchemesError] = useState(null);

  const [schemeId, setSchemeId] = useState("");
  const [scheme, setScheme] = useState(null);
  const [fields, setFields] = useState([]);
  const [formValues, setFormValues] = useState({});

  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listSchemes()
      .then(setSchemes)
      .catch((err) => setSchemesError(err));
  }, []);

  async function handleSchemeChange(e) {
    const id = e.target.value;
    setSchemeId(id);
    setResult(null);
    setError(null);
    setFormValues({});
    if (!id) {
      setScheme(null);
      setFields([]);
      return;
    }
    try {
      const fullScheme = await getScheme(id);
      setScheme(fullScheme);
      setFields(fieldsForRules(fullScheme.rules));
    } catch (err) {
      setScheme(null);
      setFields([]);
      setError(err);
    }
  }

  function handleFieldChange(e) {
    const { name, value } = e.target;
    setFormValues((v) => ({ ...v, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const criteria = buildCriteria(fields, formValues);
      const data = await quickCheck(schemeId, criteria);
      setResult(data);
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  }

  const schemeOptions = [
    { value: "", label: "Select a scheme…" },
    ...schemes.map((s) => ({ value: s.id, label: s.name })),
  ];

  return (
    <AppShell
      title="Quick eligibility checker"
      subtitle="Check likely eligibility for one scheme in seconds — no account, no sign-in, and nothing is saved. Great for checking on behalf of a friend or family member."
    >
      {schemesError && <ErrorMessage error={schemesError} />}

      <form className="card" onSubmit={handleSubmit}>
        <SelectField label="Scheme" name="scheme" value={schemeId} onChange={handleSchemeChange} options={schemeOptions} />

        {scheme && fields.length === 0 && (
          <InfoMessage>This scheme has no specific eligibility rules — everyone qualifies.</InfoMessage>
        )}

        {fields.length > 0 && (
          <div className="form-grid">
            {fields.map((field) =>
              field.type === "select" ? (
                <SelectField
                  key={field.name}
                  label={field.label}
                  name={field.name}
                  value={formValues[field.name] || ""}
                  onChange={handleFieldChange}
                  options={field.options}
                />
              ) : (
                <TextField
                  key={field.name}
                  label={field.label}
                  name={field.name}
                  type={field.type}
                  step={field.step}
                  value={formValues[field.name] || ""}
                  onChange={handleFieldChange}
                  hint={field.hint}
                />
              )
            )}
          </div>
        )}

        {error && <ErrorMessage error={error} />}

        {scheme && (
          <div className="actions">
            <button type="submit" disabled={submitting}>
              {submitting && <span className="spinner" aria-hidden="true" />}
              {submitting ? "Checking…" : "Check eligibility"}
            </button>
          </div>
        )}
      </form>

      {submitting && <LoadingMessage>Checking…</LoadingMessage>}

      {result && (
        <div className="card">
          <div className="scheme-row">
            <div>
              <strong>{result.scheme_name}</strong>
              {result.reasons.length > 0 && (
                <div className="reasons">
                  <ul>
                    {result.reasons.map((r, i) => (
                      <li key={i}>{humanizeReason(r)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            <StatusBadge status={result.status} />
          </div>

          {result.status === "eligible" && (
            <>
              <ApplyLink
                url={result.application_url}
                status={result.application_link_status}
                moreInfoUrl={result.official_scheme_url}
                schemeId={result.scheme_id}
              />
              {result.required_documents.length > 0 && (
                <div className="reasons">
                  <p className="hint">Documents needed:</p>
                  <ul>
                    {result.required_documents.map((d) => (
                      <li key={d}>{d}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {result.status === "not_eligible" && result.suggested_alternatives.length > 0 && (
            <div className="reasons">
              <p className="hint">You might also check:</p>
              <ul>
                {result.suggested_alternatives.map((alt) => (
                  <li key={alt.scheme_id}>{alt.scheme_name}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="state-message quick-check-disclaimer">{result.disclaimer}</p>
        </div>
      )}
    </AppShell>
  );
}
