import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createCitizen, listSchemes } from "../api/client";
import { SelectField, TextField } from "../components/FormField";
import { ErrorMessage } from "../components/StateMessage";
import {
  EDUCATION_LEVEL_OPTIONS,
  EMPLOYMENT_STATUS_OPTIONS,
  GENDER_OPTIONS,
  MARITAL_STATUS_OPTIONS,
  SOCIAL_CATEGORY_OPTIONS,
  TRI_STATE_OPTIONS,
  toBoolOrUndefined,
} from "../lib/profileFields";
import { setStoredCitizenId } from "../lib/storage";

const STEPS = [
  {
    key: "basics",
    title: "The essentials",
    subtitle: "Four fields — that's all we need to start matching you against schemes.",
    fields: ["name", "date_of_birth", "state", "district"],
  },
  {
    key: "work",
    title: "Household & work",
    subtitle: "Unlocks income- and occupation-based schemes. Skip anything you're unsure of.",
    fields: ["occupation", "employment_status", "annual_income", "land_holding_acres", "family_size"],
  },
  {
    key: "about",
    title: "About you",
    subtitle: "Optional — unlocks category- and welfare-specific schemes.",
    fields: ["gender", "marital_status", "social_category", "bpl_status", "disability_status", "education_level"],
  },
  {
    key: "documents",
    title: "Documents you already have",
    subtitle: "Optional — we'll tell you what's still missing either way.",
    fields: [],
  },
];

const EMPTY_FORM = {
  name: "",
  date_of_birth: "",
  state: "",
  district: "",
  gender: "",
  annual_income: "",
  occupation: "",
  social_category: "",
  disability_status: "",
  land_holding_acres: "",
  family_size: "",
  marital_status: "",
  bpl_status: "",
  education_level: "",
  employment_status: "",
};

function validate(form) {
  const errors = {};
  if (!form.name.trim()) errors.name = "Name is required.";
  if (!form.date_of_birth) {
    errors.date_of_birth = "Date of birth is required.";
  } else if (new Date(form.date_of_birth) > new Date()) {
    errors.date_of_birth = "Date of birth cannot be in the future.";
  }
  if (!form.state.trim()) errors.state = "State is required.";
  if (!form.district.trim()) errors.district = "District is required.";
  if (form.annual_income !== "" && Number(form.annual_income) < 0) {
    errors.annual_income = "Must be zero or greater.";
  }
  if (form.land_holding_acres !== "" && Number(form.land_holding_acres) < 0) {
    errors.land_holding_acres = "Must be zero or greater.";
  }
  if (form.family_size !== "") {
    const n = Number(form.family_size);
    if (n < 1) errors.family_size = "Must be at least 1.";
    else if (!Number.isInteger(n)) errors.family_size = "Must be a whole number.";
  }
  return errors;
}

export default function Onboarding() {
  const [stepIndex, setStepIndex] = useState(0);
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [documentOptions, setDocumentOptions] = useState([]);
  const [heldDocuments, setHeldDocuments] = useState(() => new Set());
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    listSchemes()
      .then((schemes) => {
        const types = new Set();
        schemes.forEach((s) => s.document_requirements.forEach((d) => types.add(d.document_type)));
        setDocumentOptions([...types].sort());
      })
      .catch(() => setDocumentOptions([]));
  }, []);

  const step = STEPS[stepIndex];
  const isLastStep = stepIndex === STEPS.length - 1;
  const isFirstStep = stepIndex === 0;

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  }

  function toggleDocument(docType) {
    setHeldDocuments((prev) => {
      const next = new Set(prev);
      if (next.has(docType)) next.delete(docType);
      else next.add(docType);
      return next;
    });
  }

  function goBack() {
    setStepIndex((i) => Math.max(0, i - 1));
  }

  function advance({ skipValidation = false } = {}) {
    if (!skipValidation) {
      const validationErrors = validate(form);
      setErrors(validationErrors);
      const blockingError = step.fields.some((f) => validationErrors[f]);
      if (blockingError) return;
    }
    setStepIndex((i) => Math.min(STEPS.length - 1, i + 1));
  }

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload = {
        name: form.name.trim(),
        date_of_birth: form.date_of_birth,
        state: form.state.trim(),
        district: form.district.trim(),
        gender: form.gender || undefined,
        annual_income: form.annual_income !== "" ? Number(form.annual_income) : undefined,
        occupation: form.occupation.trim() || undefined,
        social_category: form.social_category || undefined,
        disability_status: toBoolOrUndefined(form.disability_status),
        land_holding_acres: form.land_holding_acres !== "" ? Number(form.land_holding_acres) : undefined,
        family_size: form.family_size !== "" ? Number(form.family_size) : undefined,
        marital_status: form.marital_status || undefined,
        bpl_status: toBoolOrUndefined(form.bpl_status),
        education_level: form.education_level || undefined,
        employment_status: form.employment_status || undefined,
        documents: [...heldDocuments].map((documentType) => ({ document_type: documentType, held: true })),
      };
      const citizen = await createCitizen(payload);
      setStoredCitizenId(citizen.id);
      navigate("/dashboard");
    } catch (err) {
      const mapped = {};
      for (const fe of err.fieldErrors || []) {
        const field = fe.loc?.[1];
        if (field && field in EMPTY_FORM) mapped[field] = fe.msg;
      }
      if (Object.keys(mapped).length > 0) {
        setErrors((prev) => ({ ...prev, ...mapped }));
        const stepWithError = STEPS.findIndex((s) => s.fields.some((f) => mapped[f]));
        if (stepWithError !== -1) setStepIndex(stepWithError);
      } else {
        setSubmitError(err);
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handlePrimaryAction(e) {
    e.preventDefault();
    if (isLastStep) {
      handleSubmit();
    } else {
      advance();
    }
  }

  return (
    <main className="page wizard-page">
      <div className="wizard-progress" role="progressbar" aria-valuenow={stepIndex + 1} aria-valuemin={1} aria-valuemax={STEPS.length}>
        {STEPS.map((s, i) => (
          <span key={s.key} className={`wizard-dot${i === stepIndex ? " active" : ""}${i < stepIndex ? " done" : ""}`} />
        ))}
      </div>

      <div className="page-header">
        <span className="eyebrow">
          Step {stepIndex + 1} of {STEPS.length}
        </span>
        <h1>{step.title}</h1>
        <p>{step.subtitle}</p>
      </div>

      <form onSubmit={handlePrimaryAction} noValidate>
        {step.key === "basics" && (
          <div className="form-grid">
            <TextField label="Full name" name="name" required value={form.name} onChange={handleChange} error={errors.name} />
            <TextField
              label="Date of birth"
              name="date_of_birth"
              type="date"
              required
              value={form.date_of_birth}
              onChange={handleChange}
              error={errors.date_of_birth}
            />
            <TextField label="State" name="state" required value={form.state} onChange={handleChange} error={errors.state} hint="e.g. Maharashtra" />
            <TextField label="District" name="district" required value={form.district} onChange={handleChange} error={errors.district} />
          </div>
        )}

        {step.key === "work" && (
          <div className="form-grid">
            <TextField label="Occupation" name="occupation" value={form.occupation} onChange={handleChange} hint="e.g. farmer" />
            <SelectField
              label="Employment status"
              name="employment_status"
              value={form.employment_status}
              onChange={handleChange}
              options={EMPLOYMENT_STATUS_OPTIONS}
            />
            <TextField
              label="Annual household income (₹)"
              name="annual_income"
              type="number"
              min="0"
              value={form.annual_income}
              onChange={handleChange}
              error={errors.annual_income}
            />
            <TextField
              label="Land holding (acres)"
              name="land_holding_acres"
              type="number"
              min="0"
              step="0.1"
              value={form.land_holding_acres}
              onChange={handleChange}
              error={errors.land_holding_acres}
            />
            <TextField
              label="Family size"
              name="family_size"
              type="number"
              min="1"
              value={form.family_size}
              onChange={handleChange}
              error={errors.family_size}
            />
          </div>
        )}

        {step.key === "about" && (
          <div className="form-grid">
            <SelectField label="Gender" name="gender" value={form.gender} onChange={handleChange} options={GENDER_OPTIONS} />
            <SelectField
              label="Marital status"
              name="marital_status"
              value={form.marital_status}
              onChange={handleChange}
              options={MARITAL_STATUS_OPTIONS}
            />
            <SelectField
              label="Social category"
              name="social_category"
              value={form.social_category}
              onChange={handleChange}
              options={SOCIAL_CATEGORY_OPTIONS}
            />
            <SelectField label="BPL status" name="bpl_status" value={form.bpl_status} onChange={handleChange} options={TRI_STATE_OPTIONS} />
            <SelectField
              label="Disability status"
              name="disability_status"
              value={form.disability_status}
              onChange={handleChange}
              options={TRI_STATE_OPTIONS}
            />
            <SelectField
              label="Education level"
              name="education_level"
              value={form.education_level}
              onChange={handleChange}
              options={EDUCATION_LEVEL_OPTIONS}
            />
          </div>
        )}

        {step.key === "documents" && (
          <>
            {documentOptions.length > 0 ? (
              <div className="checkbox-grid">
                {documentOptions.map((docType) => (
                  <label className="checkbox-row" key={docType}>
                    <input type="checkbox" checked={heldDocuments.has(docType)} onChange={() => toggleDocument(docType)} />
                    {docType}
                  </label>
                ))}
              </div>
            ) : (
              <p className="hint">Loading document list…</p>
            )}
          </>
        )}

        {submitError && (
          <ErrorMessage error={submitError}>
            {submitError.status ? "Something went wrong submitting your profile. Please try again." : undefined}
          </ErrorMessage>
        )}

        <div className="actions wizard-actions">
          {!isFirstStep && (
            <button type="button" className="secondary" onClick={goBack}>
              Back
            </button>
          )}
          {!isFirstStep && !isLastStep && (
            <button type="button" className="ghost" onClick={() => advance({ skipValidation: true })}>
              Skip for now
            </button>
          )}
          <button type="submit" disabled={submitting}>
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? "Submitting…" : isLastStep ? "Find my schemes" : "Continue"}
          </button>
        </div>
      </form>
    </main>
  );
}
