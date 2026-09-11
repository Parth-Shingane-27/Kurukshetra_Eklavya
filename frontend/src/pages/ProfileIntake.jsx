import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createCitizen, listSchemes } from "../api/client";
import { SelectField, TextField } from "../components/FormField";
import JourneyNav from "../components/JourneyNav";
import { ErrorMessage } from "../components/StateMessage";

const GENDER_OPTIONS = [
  { value: "", label: "Prefer not to say" },
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "other", label: "Other" },
];

const TRI_STATE_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];

const SOCIAL_CATEGORY_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "General", label: "General" },
  { value: "OBC", label: "OBC" },
  { value: "SC", label: "SC" },
  { value: "ST", label: "ST" },
  { value: "EWS", label: "EWS" },
];

const MARITAL_STATUS_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "single", label: "Single" },
  { value: "married", label: "Married" },
  { value: "widowed", label: "Widowed" },
  { value: "divorced", label: "Divorced" },
];

const EDUCATION_LEVEL_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "none", label: "None" },
  { value: "primary", label: "Primary" },
  { value: "secondary", label: "Secondary" },
  { value: "post_matric", label: "Post-matric" },
  { value: "undergraduate", label: "Undergraduate" },
  { value: "postgraduate", label: "Postgraduate" },
];

const EMPLOYMENT_STATUS_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "employed", label: "Employed" },
  { value: "unemployed", label: "Unemployed" },
  { value: "self_employed", label: "Self-employed" },
  { value: "student", label: "Student" },
  { value: "retired", label: "Retired" },
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

function toBoolOrUndefined(value) {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}

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

export default function ProfileIntake() {
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

  async function handleSubmit(e) {
    e.preventDefault();
    const validationErrors = validate(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

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
      navigate(`/citizens/${citizen.id}/eligibility`);
    } catch (err) {
      // Map a pydantic 422's structured field errors back onto the specific form field
      // (plan.md Section 17/21: "field-level error messages") instead of one generic banner.
      const mapped = {};
      for (const fe of err.fieldErrors || []) {
        const field = fe.loc?.[1];
        if (field && field in EMPTY_FORM) mapped[field] = fe.msg;
      }
      if (Object.keys(mapped).length > 0) {
        setErrors((prev) => ({ ...prev, ...mapped }));
      } else {
        setSubmitError(err);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <JourneyNav current="profile" />
      <main className="page">
        <div className="page-header">
          <h1>Tell us about yourself</h1>
          <p>
            We&apos;ll use this to find every government scheme you may qualify for. Fields marked
            with * are required — everything else can be left blank if you&apos;re not sure.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <fieldset>
            <legend>Basic information</legend>
            <div className="form-grid">
              <TextField
                label="Full name"
                name="name"
                required
                value={form.name}
                onChange={handleChange}
                error={errors.name}
              />
              <TextField
                label="Date of birth"
                name="date_of_birth"
                type="date"
                required
                value={form.date_of_birth}
                onChange={handleChange}
                error={errors.date_of_birth}
              />
              <SelectField label="Gender" name="gender" value={form.gender} onChange={handleChange} options={GENDER_OPTIONS} />
              <TextField
                label="State"
                name="state"
                required
                value={form.state}
                onChange={handleChange}
                error={errors.state}
                hint="e.g. Maharashtra"
              />
              <TextField
                label="District"
                name="district"
                required
                value={form.district}
                onChange={handleChange}
                error={errors.district}
              />
            </div>
          </fieldset>

          <fieldset>
            <legend>Economic &amp; social information</legend>
            <div className="form-grid">
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
                label="Occupation"
                name="occupation"
                value={form.occupation}
                onChange={handleChange}
                hint="e.g. farmer"
              />
              <SelectField
                label="Social category"
                name="social_category"
                value={form.social_category}
                onChange={handleChange}
                options={SOCIAL_CATEGORY_OPTIONS}
              />
              <SelectField
                label="Disability status"
                name="disability_status"
                value={form.disability_status}
                onChange={handleChange}
                options={TRI_STATE_OPTIONS}
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
              <SelectField
                label="Marital status"
                name="marital_status"
                value={form.marital_status}
                onChange={handleChange}
                options={MARITAL_STATUS_OPTIONS}
              />
              <SelectField
                label="BPL status"
                name="bpl_status"
                value={form.bpl_status}
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
              <SelectField
                label="Employment status"
                name="employment_status"
                value={form.employment_status}
                onChange={handleChange}
                options={EMPLOYMENT_STATUS_OPTIONS}
              />
            </div>
          </fieldset>

          {documentOptions.length > 0 && (
            <fieldset>
              <legend>Documents you already have</legend>
              <p className="hint">Check anything you already hold — this helps us tell you what&apos;s still missing.</p>
              <div className="checkbox-grid">
                {documentOptions.map((docType) => (
                  <label className="checkbox-row" key={docType}>
                    <input
                      type="checkbox"
                      checked={heldDocuments.has(docType)}
                      onChange={() => toggleDocument(docType)}
                    />
                    {docType}
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          {submitError && (
            <ErrorMessage error={submitError}>
              {submitError.status ? "Something went wrong submitting your profile. Please try again." : undefined}
            </ErrorMessage>
          )}

          <div className="actions">
            <button type="submit" disabled={submitting}>
              {submitting && <span className="spinner" aria-hidden="true" />}
              {submitting ? "Submitting…" : "Find my schemes"}
            </button>
          </div>
        </form>
      </main>
    </>
  );
}
