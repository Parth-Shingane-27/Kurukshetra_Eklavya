// Shared field option lists for anything that captures or filters on a citizen profile
// (onboarding wizard, dashboard filter panel) — kept in one place so the two stay in sync.

export const GENDER_OPTIONS = [
  { value: "", label: "Prefer not to say" },
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "other", label: "Other" },
];

export const TRI_STATE_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];

export const SOCIAL_CATEGORY_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "General", label: "General" },
  { value: "OBC", label: "OBC" },
  { value: "SC", label: "SC" },
  { value: "ST", label: "ST" },
  { value: "EWS", label: "EWS" },
];

export const MARITAL_STATUS_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "single", label: "Single" },
  { value: "married", label: "Married" },
  { value: "widowed", label: "Widowed" },
  { value: "divorced", label: "Divorced" },
];

export const EDUCATION_LEVEL_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "none", label: "None" },
  { value: "primary", label: "Primary" },
  { value: "secondary", label: "Secondary" },
  { value: "post_matric", label: "Post-matric" },
  { value: "undergraduate", label: "Undergraduate" },
  { value: "postgraduate", label: "Postgraduate" },
];

export const EMPLOYMENT_STATUS_OPTIONS = [
  { value: "", label: "Not specified" },
  { value: "employed", label: "Employed" },
  { value: "unemployed", label: "Unemployed" },
  { value: "self_employed", label: "Self-employed" },
  { value: "student", label: "Student" },
  { value: "retired", label: "Retired" },
];

export function toBoolOrUndefined(value) {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}

export function boolToTriState(value) {
  if (value === true) return "true";
  if (value === false) return "false";
  return "";
}
