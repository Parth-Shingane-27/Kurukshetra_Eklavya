import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCitizen, updateCitizen } from "../api/client";
import AppShell from "../components/layout/AppShell";
import { SelectField, TextField } from "../components/FormField";
import { ErrorMessage, LoadingMessage } from "../components/StateMessage";
import {
  EDUCATION_LEVEL_OPTIONS,
  EMPLOYMENT_STATUS_OPTIONS,
  GENDER_OPTIONS,
  MARITAL_STATUS_OPTIONS,
  SOCIAL_CATEGORY_OPTIONS,
  TRI_STATE_OPTIONS,
  boolToTriState,
  toBoolOrUndefined,
} from "../lib/profileFields";
import { getStoredCitizenId } from "../lib/storage";

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

function citizenToForm(citizen) {
  return {
    name: citizen.name || "",
    date_of_birth: citizen.date_of_birth || "",
    state: citizen.state || "",
    district: citizen.district || "",
    gender: citizen.gender || "",
    annual_income: citizen.annual_income != null ? String(citizen.annual_income) : "",
    occupation: citizen.occupation || "",
    social_category: citizen.social_category || "",
    disability_status: boolToTriState(citizen.disability_status),
    land_holding_acres: citizen.land_holding_acres != null ? String(citizen.land_holding_acres) : "",
    family_size: citizen.family_size != null ? String(citizen.family_size) : "",
    marital_status: citizen.marital_status || "",
    bpl_status: boolToTriState(citizen.bpl_status),
    education_level: citizen.education_level || "",
    employment_status: citizen.employment_status || "",
  };
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

export default function Profile() {
  const navigate = useNavigate();
  const citizenId = getStoredCitizenId();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!citizenId) {
      setLoading(false);
      return;
    }
    getCitizen(citizenId)
      .then((citizen) => {
        setForm(citizenToForm(citizen));
        setLoadError(null);
      })
      .catch((err) => setLoadError(err))
      .finally(() => setLoading(false));
  }, [citizenId]);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    setSaved(false);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const validationErrors = validate(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    setSubmitting(true);
    setSubmitError(null);
    setSaved(false);
    try {
      const patch = {
        name: form.name.trim(),
        date_of_birth: form.date_of_birth,
        state: form.state.trim(),
        district: form.district.trim(),
        gender: form.gender || null,
        annual_income: form.annual_income !== "" ? Number(form.annual_income) : null,
        occupation: form.occupation.trim() || null,
        social_category: form.social_category || null,
        disability_status: toBoolOrUndefined(form.disability_status) ?? null,
        land_holding_acres: form.land_holding_acres !== "" ? Number(form.land_holding_acres) : null,
        family_size: form.family_size !== "" ? Number(form.family_size) : null,
        marital_status: form.marital_status || null,
        bpl_status: toBoolOrUndefined(form.bpl_status) ?? null,
        education_level: form.education_level || null,
        employment_status: form.employment_status || null,
      };
      await updateCitizen(citizenId, patch);
      setSaved(true);
    } catch (err) {
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

  if (!citizenId) {
    return (
      <AppShell active="profile" title="Your profile">
        <p className="hint">No profile found on this device yet.</p>
        <div className="actions">
          <button type="button" onClick={() => navigate("/onboarding")}>
            Create a profile
          </button>
        </div>
      </AppShell>
    );
  }

  if (loading) {
    return (
      <AppShell active="profile" title="Your profile">
        <LoadingMessage>Loading your profile…</LoadingMessage>
      </AppShell>
    );
  }

  if (loadError) {
    return (
      <AppShell active="profile" title="Your profile">
        <ErrorMessage
          error={loadError}
          onRetry={() => {
            setLoading(true);
            getCitizen(citizenId)
              .then((citizen) => {
                setForm(citizenToForm(citizen));
                setLoadError(null);
              })
              .catch((err) => setLoadError(err))
              .finally(() => setLoading(false));
          }}
        />
      </AppShell>
    );
  }

  return (
    <AppShell active="profile" title="Your profile" subtitle="Update your details — this keeps your scheme matches accurate.">
      <form className="card" onSubmit={handleSubmit} noValidate>
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
          <TextField label="State" name="state" required value={form.state} onChange={handleChange} error={errors.state} />
          <TextField label="District" name="district" required value={form.district} onChange={handleChange} error={errors.district} />
          <TextField label="Occupation" name="occupation" value={form.occupation} onChange={handleChange} />
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

        {submitError && <ErrorMessage error={submitError} />}
        {saved && <p className="state-message success">Profile updated.</p>}

        <div className="actions">
          <button type="submit" disabled={submitting}>
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? "Saving…" : "Save changes"}
          </button>
          <button type="button" className="secondary" onClick={() => navigate("/dashboard")}>
            Back to dashboard
          </button>
        </div>
      </form>
    </AppShell>
  );
}
