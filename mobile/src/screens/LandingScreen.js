import { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Button from "../components/Button";
import TextField from "../components/TextField";
import { getCitizen } from "../lib/api";
import { getStoredCitizenId, setStoredCitizenId } from "../lib/storage";
import { colors, radius, spacing, typography } from "../theme";

const STEPS = [
  { title: "Tell us about yourself", body: "A short, skippable form — only four fields are required." },
  { title: "Get your personalized dashboard", body: "See eligible schemes, an optimized bundle, and what to do next." },
  { title: "Explore beyond your own profile", body: "Filter and search the full scheme catalogue for family or research." },
];

export default function LandingScreen({ navigation }) {
  const [checkingSession, setCheckingSession] = useState(true);
  const [resumeId, setResumeId] = useState("");
  const [resumeError, setResumeError] = useState(null);
  const [resuming, setResuming] = useState(false);
  const [showResume, setShowResume] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const storedId = await getStoredCitizenId();
      if (!storedId) {
        if (!cancelled) setCheckingSession(false);
        return;
      }
      try {
        await getCitizen(storedId);
        if (!cancelled) navigation.replace("Main");
      } catch {
        if (!cancelled) setCheckingSession(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [navigation]);

  async function handleResume() {
    const id = resumeId.trim();
    if (!id) return;
    setResuming(true);
    setResumeError(null);
    try {
      await getCitizen(id);
      await setStoredCitizenId(id);
      navigation.replace("Main");
    } catch {
      setResumeError("We couldn't find a profile with that ID. Check it and try again.");
    } finally {
      setResuming(false);
    }
  }

  if (checkingSession) {
    return (
      <SafeAreaView style={styles.center}>
        <ActivityIndicator size="large" color={colors.accent} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.hero}>
          <View style={styles.eyebrow}>
            <Text style={styles.eyebrowText}>Citizen Benefits Assistant</Text>
          </View>
          <Text style={styles.h1}>Find every scheme you qualify for — in under a minute.</Text>
          <Text style={styles.sub}>
            Answer a few quick questions once. We&apos;ll match you against every active government
            scheme, resolve conflicts automatically, and hand you a ready-to-use application checklist.
          </Text>

          <Button title="Get started" onPress={() => navigation.navigate("Onboarding")} style={{ marginTop: spacing.lg, width: "100%" }} />

          <Button
            title={showResume ? "Hide" : "Already have a profile?"}
            variant="ghost"
            onPress={() => setShowResume((v) => !v)}
            style={{ marginTop: spacing.sm }}
          />

          {showResume && (
            <View style={{ width: "100%" }}>
              <TextField placeholder="Paste your profile ID" value={resumeId} onChangeText={setResumeId} autoCapitalize="none" />
              <Button title={resuming ? "Checking…" : "Resume"} variant="secondary" loading={resuming} onPress={handleResume} />
              {resumeError && <Text style={styles.resumeError}>{resumeError}</Text>}
            </View>
          )}
        </View>

        <View style={styles.steps}>
          {STEPS.map((s, i) => (
            <View style={styles.step} key={s.title}>
              <View style={styles.stepNumber}>
                <Text style={styles.stepNumberText}>{i + 1}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.stepTitle}>{s.title}</Text>
                <Text style={styles.stepBody}>{s.body}</Text>
              </View>
            </View>
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.bg },
  scroll: { padding: spacing.xl, gap: spacing.xxl },
  hero: { alignItems: "center", gap: spacing.sm },
  eyebrow: { backgroundColor: colors.accentSoft, borderRadius: radius.pill, paddingVertical: 4, paddingHorizontal: 12 },
  eyebrowText: { color: colors.accent, fontWeight: "700", fontSize: 12, letterSpacing: 0.4 },
  h1: { ...typography.h1, textAlign: "center", marginTop: spacing.sm },
  sub: { ...typography.muted, textAlign: "center" },
  resumeError: { color: colors.danger, fontSize: 12.5, marginTop: 4 },
  steps: { gap: spacing.md },
  step: {
    flexDirection: "row",
    gap: spacing.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  stepNumber: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  stepNumberText: { color: colors.accentContrast, fontWeight: "700" },
  stepTitle: { fontWeight: "700", color: colors.text, marginBottom: 2 },
  stepBody: { ...typography.small },
});
