import {
  EDUCATION_LEVEL_OPTIONS,
  EMPLOYMENT_STATUS_OPTIONS,
  GENDER_OPTIONS,
  MARITAL_STATUS_OPTIONS,
  SOCIAL_CATEGORY_OPTIONS,
  TRI_STATE_OPTIONS,
} from "./profileFields";

// Maps a Citizen profile field name to how the Quick Checker should render/collect it — reused
// from the same option sets Onboarding/FilterPanel already use, so a "widowed"/"SC"/etc. value
// entered here means exactly the same thing it would on the full profile form.
const FIELD_META = {
  state: { label: "State", type: "text", hint: "e.g. Maharashtra" },
  district: { label: "District", type: "text" },
  occupation: { label: "Occupation", type: "text", hint: "e.g. farmer" },
  employment_status: { label: "Employment status", type: "select", options: EMPLOYMENT_STATUS_OPTIONS },
  education_level: { label: "Education level", type: "select", options: EDUCATION_LEVEL_OPTIONS },
  social_category: { label: "Social category", type: "select", options: SOCIAL_CATEGORY_OPTIONS },
  bpl_status: { label: "BPL status", type: "select", options: TRI_STATE_OPTIONS, boolean: true },
  disability_status: { label: "Disability status", type: "select", options: TRI_STATE_OPTIONS, boolean: true },
  marital_status: { label: "Marital status", type: "select", options: MARITAL_STATUS_OPTIONS },
  gender: { label: "Gender", type: "select", options: GENDER_OPTIONS },
  annual_income: { label: "Annual income (₹)", type: "number" },
  land_holding_acres: { label: "Land holding (acres)", type: "number", step: "0.1" },
  family_size: { label: "Family size", type: "number" },
  // A rule referencing "age" is asked as a date of birth — friendlier for a citizen to enter,
  // and the backend derives age from it the identical way FR-001's structured form does.
  age: { label: "Date of birth", type: "date", asCriteriaField: "date_of_birth" },
};

// One entry per unique field_name referenced across a scheme's rules — never the scheme's
// full profile-shaped field set, matching FR-013's "just the fields its rules reference."
export function fieldsForRules(rules) {
  const seen = new Set();
  const fields = [];
  for (const r of rules || []) {
    if (seen.has(r.field_name)) continue;
    seen.add(r.field_name);
    const meta = FIELD_META[r.field_name] || { label: r.field_name, type: "text" };
    fields.push({ name: r.field_name, ...meta });
  }
  return fields;
}

export function buildCriteria(fields, formValues) {
  const criteria = {};
  for (const field of fields) {
    const raw = formValues[field.name];
    if (raw === undefined || raw === "") continue;
    const criteriaKey = field.asCriteriaField || field.name;
    if (field.boolean) {
      if (raw === "true") criteria[criteriaKey] = true;
      else if (raw === "false") criteria[criteriaKey] = false;
    } else if (field.type === "number") {
      criteria[criteriaKey] = Number(raw);
    } else {
      criteria[criteriaKey] = raw;
    }
  }
  return criteria;
}
