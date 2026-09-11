import { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Button from "../components/Button";
import ChipSelect from "../components/ChipSelect";
import { ErrorMessage } from "../components/StateMessage";
import TextField from "../components/TextField";
import { createCitizen, listSchemes } from "../lib/api";
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
import { colors, radius, spacing, typography } from "../theme";

const STEPS = [
  { key: "basics", title: "The essentials", subtitle: "Four fields — that's all we need to start matching you against schemes.", fields: ["name", "date_of_birth", "state", "district"] },
  { key: "work", title: "Household & work", subtitle: "Unlocks income- and occupation-based schemes. Skip anything you're unsure of.", fields: [] },
  { key: "about", title: "About you", subtitle: "Optional — unlocks category- and welfare-specific schemes.", fields: [] },
  { key: "documents", title: "Documents you already have", subtitle: "Optional — we'll tell you what's still missing either way.", fields: [] },
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

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function validate(form) {
  const errors = {};
  if (!form.name.trim()) errors.name = "Name is required.";
  if (!form.date_of_birth) {
    errors.date_of_birth = "Date of birth is required.";
  } else if (!DATE_RE.test(form.date_of_birth)) {
    errors.date_of_birth = "Use the format YYYY-MM-DD.";
  } else if (new Date(form.date_of_birth) > new Date()) {
    errors.date_of_birth = "Date of birth cannot be in the future.";
  }
  if (!form.state.trim()) errors.state = "State is required.";
  if (!form.district.trim()) errors.district = "District is required.";
  if (form.annual_income !== "" && Number(form.annual_income) < 0) errors.annual_income = "Must be zero or greater.";
  if (form.land_holding_acres !== "" && Number(form.land_holding_acres) < 0) errors.land_holding_acres = "Must be zero or greater.";
  if (form.family_size !== "") {
    const n = Number(form.family_size);
    if (n < 1) errors.family_size = "Must be at least 1.";
    else if (!Number.isInteger(n)) errors.family_size = "Must be a whole number.";
  }
  return errors;
}

export default function OnboardingScreen({ navigation }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [documentOptions, setDocumentOptions] = useState([]);
  const [heldDocuments, setHeldDocuments] = useState(() => new Set());
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

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

  function setField(name, value) {
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

  function advance({ skipValidation = false } = {}) {
    if (!skipValidation) {
      const validationErrors = validate(form);
      setErrors(validationErrors);
      const blockingError = step.fields.some((f) => validationErrors[f]);
      if (blockingError) return;
    }
    setStepIndex((i) => Math.min(STEPS.length - 1, i + 1));
  }

  function goBack() {
    setStepIndex((i) => Math.max(0, i - 1));
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
      await setStoredCitizenId(citizen.id);
      navigation.replace("Main");
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

  function handlePrimary() {
    if (isLastStep) handleSubmit();
    else advance();
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.progress}>
        {STEPS.map((s, i) => (
          <View key={s.key} style={[styles.dot, i <= stepIndex && styles.dotActive]} />
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.eyebrow}>
          Step {stepIndex + 1} of {STEPS.length}
        </Text>
        <Text style={styles.h1}>{step.title}</Text>
        <Text style={styles.sub}>{step.subtitle}</Text>

        {step.key === "basics" && (
          <>
            <TextField label="Full name" required value={form.name} onChangeText={(v) => setField("name", v)} error={errors.name} />
            <TextField
              label="Date of birth"
              required
              value={form.date_of_birth}
              onChangeText={(v) => setField("date_of_birth", v)}
              error={errors.date_of_birth}
              placeholder="YYYY-MM-DD"
              keyboardType="numbers-and-punctuation"
            />
            <TextField label="State" required value={form.state} onChangeText={(v) => setField("state", v)} error={errors.state} hint="e.g. Maharashtra" />
            <TextField label="District" required value={form.district} onChangeText={(v) => setField("district", v)} error={errors.district} />
          </>
        )}

        {step.key === "work" && (
          <>
            <TextField label="Occupation" value={form.occupation} onChangeText={(v) => setField("occupation", v)} hint="e.g. farmer" />
            <ChipSelect label="Employment status" value={form.employment_status} onChange={(v) => setField("employment_status", v)} options={EMPLOYMENT_STATUS_OPTIONS} />
            <TextField label="Annual household income (₹)" value={form.annual_income} onChangeText={(v) => setField("annual_income", v)} error={errors.annual_income} keyboardType="numeric" />
            <TextField label="Land holding (acres)" value={form.land_holding_acres} onChangeText={(v) => setField("land_holding_acres", v)} error={errors.land_holding_acres} keyboardType="numeric" />
            <TextField label="Family size" value={form.family_size} onChangeText={(v) => setField("family_size", v)} error={errors.family_size} keyboardType="number-pad" />
          </>
        )}

        {step.key === "about" && (
          <>
            <ChipSelect label="Gender" value={form.gender} onChange={(v) => setField("gender", v)} options={GENDER_OPTIONS} />
            <ChipSelect label="Marital status" value={form.marital_status} onChange={(v) => setField("marital_status", v)} options={MARITAL_STATUS_OPTIONS} />
            <ChipSelect label="Social category" value={form.social_category} onChange={(v) => setField("social_category", v)} options={SOCIAL_CATEGORY_OPTIONS} />
            <ChipSelect label="BPL status" value={form.bpl_status} onChange={(v) => setField("bpl_status", v)} options={TRI_STATE_OPTIONS} />
            <ChipSelect label="Disability status" value={form.disability_status} onChange={(v) => setField("disability_status", v)} options={TRI_STATE_OPTIONS} />
            <ChipSelect label="Education level" value={form.education_level} onChange={(v) => setField("education_level", v)} options={EDUCATION_LEVEL_OPTIONS} />
          </>
        )}

        {step.key === "documents" && (
          <View style={{ gap: 6 }}>
            {documentOptions.length > 0 ? (
              documentOptions.map((docType) => {
                const checked = heldDocuments.has(docType);
                return (
                  <Pressable key={docType} style={styles.checkRow} onPress={() => toggleDocument(docType)}>
                    <View style={[styles.checkbox, checked && styles.checkboxChecked]}>
                      {checked && <Text style={styles.checkboxMark}>✓</Text>}
                    </View>
                    <Text style={styles.checkLabel}>{docType}</Text>
                  </Pressable>
                );
              })
            ) : (
              <Text style={typography.muted}>Loading document list…</Text>
            )}
          </View>
        )}

        {submitError && (
          <ErrorMessage error={submitError}>
            {submitError.status ? "Something went wrong submitting your profile. Please try again." : undefined}
          </ErrorMessage>
        )}
      </ScrollView>

      <View style={styles.actions}>
        {!isFirstStep && <Button title="Back" variant="secondary" onPress={goBack} style={{ flex: 1 }} />}
        {!isFirstStep && !isLastStep && (
          <Button title="Skip" variant="ghost" onPress={() => advance({ skipValidation: true })} style={{ flex: 1 }} />
        )}
        <Button
          title={submitting ? "Submitting…" : isLastStep ? "Find my schemes" : "Continue"}
          loading={submitting}
          onPress={handlePrimary}
          style={{ flex: 2 }}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  progress: { flexDirection: "row", gap: 6, paddingHorizontal: spacing.xl, paddingTop: spacing.md },
  dot: { flex: 1, height: 5, borderRadius: 999, backgroundColor: colors.border },
  dotActive: { backgroundColor: colors.accent },
  scroll: { padding: spacing.xl, paddingBottom: spacing.xxl },
  eyebrow: { color: colors.accent, fontWeight: "700", fontSize: 12, letterSpacing: 0.4, marginTop: spacing.md },
  h1: { ...typography.h1, marginTop: 4, marginBottom: 4 },
  sub: { ...typography.muted, marginBottom: spacing.lg },
  actions: {
    flexDirection: "row",
    gap: spacing.sm,
    padding: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
  },
  checkRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingVertical: 8 },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 1.5,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxChecked: { backgroundColor: colors.accent, borderColor: colors.accent },
  checkboxMark: { color: colors.accentContrast, fontSize: 13, fontWeight: "700" },
  checkLabel: { fontSize: 14.5, color: colors.text, flexShrink: 1 },
});
