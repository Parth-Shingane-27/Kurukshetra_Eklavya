import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import Button from "./Button";
import ChipSelect from "./ChipSelect";
import TextField from "./TextField";
import {
  EDUCATION_LEVEL_OPTIONS,
  EMPLOYMENT_STATUS_OPTIONS,
  GENDER_OPTIONS,
  MARITAL_STATUS_OPTIONS,
  SOCIAL_CATEGORY_OPTIONS,
  TRI_STATE_OPTIONS,
} from "../lib/profileFields";
import { colors, radius, spacing } from "../theme";

// Mirrors the field set captured during onboarding, so a citizen can explore the catalogue
// under variations of their own profile (or someone else's) without editing their saved profile.
export default function FilterSheet({ filters, onFieldChange, onReset, onClear, hasChanges }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <View style={styles.panel}>
      <View style={styles.header}>
        <Button title={expanded ? "Filters ▲" : "Filters ▼"} variant="secondary" onPress={() => setExpanded((v) => !v)} style={styles.toggle} />
        {hasChanges && (
          <>
            <Button title="Reset" variant="ghost" onPress={onReset} style={styles.small} />
            <Button title="Clear" variant="ghost" onPress={onClear} style={styles.small} />
          </>
        )}
      </View>

      {expanded && (
        <View style={styles.grid}>
          <TextField label="State" value={filters.state} onChangeText={(v) => onFieldChange("state", v)} />
          <TextField label="Occupation" value={filters.occupation} onChangeText={(v) => onFieldChange("occupation", v)} hint="matches exactly, e.g. farmer" />
          <ChipSelect label="Employment status" value={filters.employment_status} onChange={(v) => onFieldChange("employment_status", v)} options={EMPLOYMENT_STATUS_OPTIONS} />
          <ChipSelect label="Education level" value={filters.education_level} onChange={(v) => onFieldChange("education_level", v)} options={EDUCATION_LEVEL_OPTIONS} />
          <ChipSelect label="Social category" value={filters.social_category} onChange={(v) => onFieldChange("social_category", v)} options={SOCIAL_CATEGORY_OPTIONS} />
          <ChipSelect label="BPL status" value={filters.bpl_status} onChange={(v) => onFieldChange("bpl_status", v)} options={TRI_STATE_OPTIONS} />
          <ChipSelect label="Disability status" value={filters.disability_status} onChange={(v) => onFieldChange("disability_status", v)} options={TRI_STATE_OPTIONS} />
          <ChipSelect label="Marital status" value={filters.marital_status} onChange={(v) => onFieldChange("marital_status", v)} options={MARITAL_STATUS_OPTIONS} />
          <ChipSelect label="Gender" value={filters.gender} onChange={(v) => onFieldChange("gender", v)} options={GENDER_OPTIONS} />
          <TextField label="Age" value={filters.age} onChangeText={(v) => onFieldChange("age", v)} keyboardType="number-pad" />
          <TextField label="Annual income (₹)" value={filters.annual_income} onChangeText={(v) => onFieldChange("annual_income", v)} keyboardType="numeric" />
          <TextField label="Land holding (acres)" value={filters.land_holding_acres} onChangeText={(v) => onFieldChange("land_holding_acres", v)} keyboardType="numeric" />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.sm,
    marginBottom: spacing.md,
  },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.sm, flexWrap: "wrap" },
  toggle: { paddingVertical: 6, paddingHorizontal: 12 },
  small: { paddingVertical: 4, paddingHorizontal: 8 },
  grid: { marginTop: spacing.sm },
});
