import { useState } from "react";
import { SelectField, TextField } from "./FormField";
import {
  EDUCATION_LEVEL_OPTIONS,
  EMPLOYMENT_STATUS_OPTIONS,
  GENDER_OPTIONS,
  MARITAL_STATUS_OPTIONS,
  SOCIAL_CATEGORY_OPTIONS,
  TRI_STATE_OPTIONS,
} from "../lib/profileFields";

// Mirrors the field set captured during onboarding, so a citizen can explore the catalogue
// under variations of their own profile (or someone else's) without editing their saved profile.
export default function FilterPanel({ filters, onFieldChange, onReset, onClear, hasChanges }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="filter-panel">
      <div className="filter-panel-header">
        <button
          type="button"
          className="chip-toggle"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
        >
          Filters {expanded ? "▲" : "▼"}
        </button>
        {hasChanges && (
          <>
            <button type="button" className="ghost small" onClick={onReset}>
              Reset to my profile
            </button>
            <button type="button" className="ghost small" onClick={onClear}>
              Clear all
            </button>
          </>
        )}
      </div>

      {expanded && (
        <div className="form-grid filter-grid">
          <TextField label="State" name="state" value={filters.state} onChange={onFieldChange} />
          <TextField
            label="Occupation"
            name="occupation"
            value={filters.occupation}
            onChange={onFieldChange}
            hint="matches exactly, e.g. farmer"
          />
          <SelectField
            label="Employment status"
            name="employment_status"
            value={filters.employment_status}
            onChange={onFieldChange}
            options={EMPLOYMENT_STATUS_OPTIONS}
          />
          <SelectField
            label="Education level"
            name="education_level"
            value={filters.education_level}
            onChange={onFieldChange}
            options={EDUCATION_LEVEL_OPTIONS}
          />
          <SelectField
            label="Social category"
            name="social_category"
            value={filters.social_category}
            onChange={onFieldChange}
            options={SOCIAL_CATEGORY_OPTIONS}
          />
          <SelectField
            label="BPL status"
            name="bpl_status"
            value={filters.bpl_status}
            onChange={onFieldChange}
            options={TRI_STATE_OPTIONS}
          />
          <SelectField
            label="Disability status"
            name="disability_status"
            value={filters.disability_status}
            onChange={onFieldChange}
            options={TRI_STATE_OPTIONS}
          />
          <SelectField
            label="Marital status"
            name="marital_status"
            value={filters.marital_status}
            onChange={onFieldChange}
            options={MARITAL_STATUS_OPTIONS}
          />
          <SelectField label="Gender" name="gender" value={filters.gender} onChange={onFieldChange} options={GENDER_OPTIONS} />
          <TextField label="Age" name="age" type="number" min="0" value={filters.age} onChange={onFieldChange} />
          <TextField
            label="Annual income (₹)"
            name="annual_income"
            type="number"
            min="0"
            value={filters.annual_income}
            onChange={onFieldChange}
          />
          <TextField
            label="Land holding (acres)"
            name="land_holding_acres"
            type="number"
            min="0"
            step="0.1"
            value={filters.land_holding_acres}
            onChange={onFieldChange}
          />
        </div>
      )}
    </div>
  );
}
