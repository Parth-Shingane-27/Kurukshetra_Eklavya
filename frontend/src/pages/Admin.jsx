import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createConflictRule,
  createScheme,
  listConflictRules,
  listSchemes,
  updateScheme,
} from "../api/client";
import { getUser, isLoggedIn, subscribe } from "../auth/session";
import { SelectField, TextField } from "../components/FormField";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";

const OPERATOR_OPTIONS = [
  { value: "=", label: "= (equals)" },
  { value: "<", label: "< (less than)" },
  { value: "<=", label: "<= (less than or equal)" },
  { value: ">", label: "> (greater than)" },
  { value: ">=", label: ">= (greater than or equal)" },
  { value: "in", label: "in (comma-separated list)" },
];

const EMPTY_SCHEME_FORM = {
  name: "",
  description: "",
  issuing_authority: "",
  category: "",
  benefit_type: "",
  benefit_value_estimate: "",
  conflict_group: "",
  source_reference: "",
  application_link: "",
};

const EMPTY_CONFLICT_FORM = { scheme_a_id: "", scheme_b_id: "", conflict_type: "mutually_exclusive", reason: "" };

function parseRuleValue(rule) {
  if (rule.operator === "in") {
    return rule.value.split(",").map((v) => v.trim()).filter(Boolean);
  }
  const trimmed = rule.value.trim();
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (trimmed !== "" && !Number.isNaN(Number(trimmed))) return Number(trimmed);
  return trimmed;
}

// Maps a pydantic 422's structured {loc, msg} list back onto the specific top-level field,
// rule row, or document-requirement row that caused it (plan.md Section 17/21: "Rule
// validation errors shown per field" / "Rule-field-level error in Admin UI").
function mapFieldErrors(fieldErrors) {
  const top = {};
  const ruleErrors = {};
  const docErrors = {};
  const other = [];
  for (const fe of fieldErrors) {
    const loc = fe.loc || [];
    if (loc[0] !== "body") {
      other.push(fe.msg);
    } else if (loc[1] === "rules" && typeof loc[2] === "number") {
      const idx = loc[2];
      const field = loc[3] || "_row";
      ruleErrors[idx] = { ...ruleErrors[idx], [field]: fe.msg };
    } else if (loc[1] === "document_requirements" && typeof loc[2] === "number") {
      const idx = loc[2];
      const field = loc[3] || "_row";
      docErrors[idx] = { ...docErrors[idx], [field]: fe.msg };
    } else if (loc.length === 2) {
      top[loc[1]] = fe.msg;
    } else {
      other.push(fe.msg);
    }
  }
  return { top, ruleErrors, docErrors, other };
}

export default function Admin() {
  const [sessionUser, setSessionUser] = useState(getUser());
  const isAdmin = isLoggedIn() && sessionUser?.role === "admin";
  const [schemes, setSchemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_SCHEME_FORM);
  const [rules, setRules] = useState([]);
  const [docs, setDocs] = useState([]);
  const [topErrors, setTopErrors] = useState({});
  const [ruleErrors, setRuleErrors] = useState({});
  const [docErrors, setDocErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [conflictRules, setConflictRules] = useState([]);
  const [conflictLoadError, setConflictLoadError] = useState(null);
  const [conflictForm, setConflictForm] = useState(EMPTY_CONFLICT_FORM);
  const [conflictFormError, setConflictFormError] = useState(null);
  const [conflictSubmitting, setConflictSubmitting] = useState(false);

  const loadSchemes = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listSchemes({ includeInactive: true });
      setSchemes(data);
      setLoadError(null);
    } catch (err) {
      setLoadError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadConflictRulesList = useCallback(async () => {
    try {
      const data = await listConflictRules();
      setConflictRules(data);
      setConflictLoadError(null);
    } catch (err) {
      setConflictLoadError(err);
    }
  }, []);

  useEffect(() => {
    loadSchemes();
    loadConflictRulesList();
  }, [loadSchemes, loadConflictRulesList]);

  useEffect(() => subscribe(() => setSessionUser(getUser())), []);

  function handleFormChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  }

  function addRule() {
    setRules((r) => [...r, { field_name: "", operator: "=", value: "", logical_group: "A" }]);
  }
  function updateRule(index, patch) {
    setRules((r) => r.map((rule, i) => (i === index ? { ...rule, ...patch } : rule)));
  }
  function removeRule(index) {
    setRules((r) => r.filter((_, i) => i !== index));
  }

  function addDoc() {
    setDocs((d) => [...d, { document_type: "", is_mandatory: true }]);
  }
  function updateDoc(index, patch) {
    setDocs((d) => d.map((doc, i) => (i === index ? { ...doc, ...patch } : doc)));
  }
  function removeDoc(index) {
    setDocs((d) => d.filter((_, i) => i !== index));
  }

  function clearFormErrors() {
    setFormError(null);
    setTopErrors({});
    setRuleErrors({});
    setDocErrors({});
  }

  function startEdit(scheme) {
    setEditingId(scheme.id);
    setForm({
      name: scheme.name,
      description: scheme.description || "",
      issuing_authority: scheme.issuing_authority || "",
      category: scheme.category,
      benefit_type: scheme.benefit_type,
      benefit_value_estimate: String(scheme.benefit_value_estimate),
      conflict_group: scheme.conflict_group || "",
      source_reference: scheme.source_reference || "",
      application_link: scheme.application_link || "",
    });
    setRules(
      scheme.rules.map((r) => ({
        field_name: r.field_name,
        operator: r.operator,
        value: Array.isArray(r.value) ? r.value.join(",") : String(r.value),
        logical_group: r.logical_group || "",
      }))
    );
    setDocs(scheme.document_requirements.map((d) => ({ document_type: d.document_type, is_mandatory: d.is_mandatory })));
    clearFormErrors();
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(EMPTY_SCHEME_FORM);
    setRules([]);
    setDocs([]);
    clearFormErrors();
  }

  async function toggleActive(scheme) {
    setLoadError(null);
    try {
      await updateScheme(scheme.id, { is_active: !scheme.is_active });
      await loadSchemes();
    } catch (err) {
      setLoadError(err);
    }
  }

  async function handleSubmitScheme(e) {
    e.preventDefault();
    clearFormErrors();
    if (!isAdmin) {
      setFormError("Log in with an admin account first.");
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        issuing_authority: form.issuing_authority.trim() || undefined,
        category: form.category.trim(),
        benefit_type: form.benefit_type.trim(),
        benefit_value_estimate: Number(form.benefit_value_estimate),
        conflict_group: form.conflict_group.trim() || undefined,
        source_reference: form.source_reference.trim() || undefined,
        application_link: form.application_link.trim() || undefined,
        rules: rules.map((r) => ({
          field_name: r.field_name.trim(),
          operator: r.operator,
          value: parseRuleValue(r),
          logical_group: r.logical_group.trim() || undefined,
        })),
        document_requirements: docs.map((d) => ({
          document_type: d.document_type.trim(),
          is_mandatory: d.is_mandatory,
        })),
      };
      if (editingId) {
        await updateScheme(editingId, payload);
      } else {
        await createScheme(payload);
      }
      cancelEdit();
      await loadSchemes();
    } catch (err) {
      if (err.fieldErrors && err.fieldErrors.length > 0) {
        const mapped = mapFieldErrors(err.fieldErrors);
        setTopErrors(mapped.top);
        setRuleErrors(mapped.ruleErrors);
        setDocErrors(mapped.docErrors);
        const hasFieldMapping =
          Object.keys(mapped.top).length || Object.keys(mapped.ruleErrors).length || Object.keys(mapped.docErrors).length;
        if (!hasFieldMapping) setFormError(err);
      } else {
        setFormError(err);
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleConflictFormChange(e) {
    const { name, value } = e.target;
    setConflictForm((f) => ({ ...f, [name]: value }));
  }

  async function handleDeclareConflict(e) {
    e.preventDefault();
    setConflictFormError(null);
    if (!isAdmin) {
      setConflictFormError("Log in with an admin account first.");
      return;
    }
    if (!conflictForm.scheme_a_id || !conflictForm.scheme_b_id) {
      setConflictFormError("Select two different schemes.");
      return;
    }
    setConflictSubmitting(true);
    try {
      await createConflictRule({
        scheme_a_id: conflictForm.scheme_a_id,
        scheme_b_id: conflictForm.scheme_b_id,
        conflict_type: conflictForm.conflict_type.trim() || "mutually_exclusive",
        reason: conflictForm.reason.trim() || undefined,
      });
      setConflictForm(EMPTY_CONFLICT_FORM);
      await loadConflictRulesList();
    } catch (err) {
      setConflictFormError(err);
    } finally {
      setConflictSubmitting(false);
    }
  }

  const schemeOptions = [{ value: "", label: "Select a scheme…" }, ...schemes.map((s) => ({ value: s.id, label: s.name }))];

  return (
    <main className="page">
      <div className="page-header">
        <h1>Scheme knowledge base admin</h1>
        <p>Curate the scheme catalogue without redeploying code (FR-011).</p>
      </div>

      <div className="card">
        {isAdmin ? (
          <InfoMessage>Logged in as {sessionUser.email} (admin) — write actions below are enabled.</InfoMessage>
        ) : (
          <InfoMessage>
            <Link to="/login">Log in</Link> with an admin account to create/edit schemes or declare
            conflicts. Browsing the existing knowledge base below doesn't require logging in.
          </InfoMessage>
        )}
      </div>

      <div className="card">
        <h2>Schemes</h2>
        {loading && <LoadingMessage>Loading schemes…</LoadingMessage>}
        {loadError && <ErrorMessage error={loadError} onRetry={loadSchemes} />}
        {!loading && schemes.length === 0 && <InfoMessage>No schemes in the knowledge base yet.</InfoMessage>}
        {schemes.map((s) => (
          <div className="scheme-row" key={s.id}>
            <div>
              <strong>{s.name}</strong>
              <div className="reasons">
                {s.category} · ₹{s.benefit_value_estimate.toLocaleString()}
                {s.conflict_group && ` · conflict group: ${s.conflict_group}`}
                {!s.is_active && " · inactive"}
              </div>
              {s.application_link && (
                <div className="reasons">
                  <a href={s.application_link} target="_blank" rel="noreferrer">
                    Registration / application form ↗
                  </a>
                </div>
              )}
            </div>
            <div className="actions">
              <button type="button" className="secondary" onClick={() => startEdit(s)}>
                Edit
              </button>
              <button type="button" className="secondary" onClick={() => toggleActive(s)}>
                {s.is_active ? "Deactivate" : "Reactivate"}
              </button>
            </div>
          </div>
        ))}
      </div>

      <form className="card" onSubmit={handleSubmitScheme}>
        <h2>{editingId ? "Edit scheme" : "Add a new scheme"}</h2>
        <div className="form-grid">
          <TextField
            label="Name"
            name="name"
            required
            value={form.name}
            onChange={handleFormChange}
            error={topErrors.name}
          />
          <TextField
            label="Category"
            name="category"
            required
            value={form.category}
            onChange={handleFormChange}
            error={topErrors.category}
          />
          <TextField
            label="Benefit type"
            name="benefit_type"
            required
            value={form.benefit_type}
            onChange={handleFormChange}
            error={topErrors.benefit_type}
            hint="e.g. cash_transfer"
          />
          <TextField
            label="Benefit value estimate (₹)"
            name="benefit_value_estimate"
            type="number"
            required
            value={form.benefit_value_estimate}
            onChange={handleFormChange}
            error={topErrors.benefit_value_estimate}
          />
          <TextField
            label="Issuing authority"
            name="issuing_authority"
            value={form.issuing_authority}
            onChange={handleFormChange}
            error={topErrors.issuing_authority}
          />
          <TextField
            label="Conflict group"
            name="conflict_group"
            value={form.conflict_group}
            onChange={handleFormChange}
            error={topErrors.conflict_group}
            hint="Schemes sharing a group conflict (BR-005)"
          />
          <TextField
            label="Source reference (URL)"
            name="source_reference"
            value={form.source_reference}
            onChange={handleFormChange}
            error={topErrors.source_reference}
          />
          <TextField
            label="Registration / application form link"
            name="application_link"
            value={form.application_link}
            onChange={handleFormChange}
            error={topErrors.application_link}
            hint="Official government URL where a citizen applies for this scheme"
          />
        </div>
        <div className="field">
          <label htmlFor="description">Description</label>
          <input id="description" name="description" value={form.description} onChange={handleFormChange} />
        </div>

        <fieldset>
          <legend>Eligibility rules</legend>
          {rules.map((rule, i) => (
            <div key={i}>
              <div className="form-grid">
                <TextField
                  label="Field name"
                  name={`rule_field_${i}`}
                  value={rule.field_name}
                  onChange={(e) => updateRule(i, { field_name: e.target.value })}
                  hint="e.g. annual_income, age, bpl_status"
                  error={ruleErrors[i]?.field_name}
                />
                <SelectField
                  label="Operator"
                  name={`rule_operator_${i}`}
                  value={rule.operator}
                  onChange={(e) => updateRule(i, { operator: e.target.value })}
                  options={OPERATOR_OPTIONS}
                  error={ruleErrors[i]?.operator}
                />
                <TextField
                  label="Value"
                  name={`rule_value_${i}`}
                  value={rule.value}
                  onChange={(e) => updateRule(i, { value: e.target.value })}
                  hint={rule.operator === "in" ? "comma-separated, e.g. SC,ST" : "e.g. 250000 or true"}
                  error={ruleErrors[i]?.value}
                />
                <TextField
                  label="Logical group"
                  name={`rule_group_${i}`}
                  value={rule.logical_group}
                  onChange={(e) => updateRule(i, { logical_group: e.target.value })}
                  hint="Same group = AND; different groups = OR"
                  error={ruleErrors[i]?.logical_group}
                />
                <div className="actions">
                  <button type="button" className="secondary" onClick={() => removeRule(i)}>
                    Remove rule
                  </button>
                </div>
              </div>
              {ruleErrors[i]?._row && <p className="field-error">{ruleErrors[i]._row}</p>}
            </div>
          ))}
          <button type="button" className="secondary" onClick={addRule}>
            + Add rule
          </button>
        </fieldset>

        <fieldset>
          <legend>Document requirements</legend>
          {docs.map((doc, i) => (
            <div key={i}>
              <div className="form-grid">
                <TextField
                  label="Document type"
                  name={`doc_type_${i}`}
                  value={doc.document_type}
                  onChange={(e) => updateDoc(i, { document_type: e.target.value })}
                  error={docErrors[i]?.document_type}
                />
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={doc.is_mandatory}
                    onChange={(e) => updateDoc(i, { is_mandatory: e.target.checked })}
                  />
                  Mandatory
                </label>
                <div className="actions">
                  <button type="button" className="secondary" onClick={() => removeDoc(i)}>
                    Remove document
                  </button>
                </div>
              </div>
              {docErrors[i]?._row && <p className="field-error">{docErrors[i]._row}</p>}
            </div>
          ))}
          <button type="button" className="secondary" onClick={addDoc}>
            + Add document requirement
          </button>
        </fieldset>

        {formError && typeof formError === "string" && <ErrorMessage>{formError}</ErrorMessage>}
        {formError && typeof formError !== "string" && (
          <ErrorMessage error={formError}>
            {formError.status ? "Please review the highlighted fields above and try again." : undefined}
          </ErrorMessage>
        )}

        <div className="actions">
          <button type="submit" disabled={submitting}>
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? "Saving…" : editingId ? "Save changes" : "Create scheme"}
          </button>
          {editingId && (
            <button type="button" className="secondary" onClick={cancelEdit}>
              Cancel edit
            </button>
          )}
        </div>
      </form>

      <div className="card">
        <h2>Declared conflicts (BR-004)</h2>
        <p className="hint">
          Distinct from the "Conflict group" field above (BR-005) — this declares an explicit pair of
          schemes as mutually exclusive.
        </p>
        {conflictLoadError && <ErrorMessage error={conflictLoadError} onRetry={loadConflictRulesList} />}
        {conflictRules.length === 0 && !conflictLoadError && (
          <InfoMessage>No conflicts declared yet.</InfoMessage>
        )}
        {conflictRules.map((c) => (
          <div className="scheme-row" key={c.id}>
            <div>
              <strong>
                {c.scheme_a_name} vs. {c.scheme_b_name}
              </strong>
              <div className="reasons">
                {c.conflict_type}
                {c.reason && ` — ${c.reason}`}
              </div>
            </div>
          </div>
        ))}
      </div>

      <form className="card" onSubmit={handleDeclareConflict}>
        <h2>Declare a new conflict</h2>
        <div className="form-grid">
          <SelectField
            label="Scheme A"
            name="scheme_a_id"
            value={conflictForm.scheme_a_id}
            onChange={handleConflictFormChange}
            options={schemeOptions}
          />
          <SelectField
            label="Scheme B"
            name="scheme_b_id"
            value={conflictForm.scheme_b_id}
            onChange={handleConflictFormChange}
            options={schemeOptions}
          />
          <TextField
            label="Conflict type"
            name="conflict_type"
            value={conflictForm.conflict_type}
            onChange={handleConflictFormChange}
            hint="e.g. mutually_exclusive"
          />
          <TextField label="Reason" name="reason" value={conflictForm.reason} onChange={handleConflictFormChange} />
        </div>

        {conflictFormError && typeof conflictFormError === "string" && (
          <ErrorMessage>{conflictFormError}</ErrorMessage>
        )}
        {conflictFormError && typeof conflictFormError !== "string" && <ErrorMessage error={conflictFormError} />}

        <div className="actions">
          <button type="submit" disabled={conflictSubmitting}>
            {conflictSubmitting && <span className="spinner" aria-hidden="true" />}
            {conflictSubmitting ? "Declaring…" : "Declare conflict"}
          </button>
        </div>
      </form>
    </main>
  );
}
