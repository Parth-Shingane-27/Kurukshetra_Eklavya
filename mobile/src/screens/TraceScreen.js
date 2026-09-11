import { useCallback, useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { getTrace } from "../lib/api";
import { colors, radius, spacing, typography } from "../theme";

const STEP_LABELS = {
  eligibility: "Eligibility evaluation",
  conflicts: "Conflict detection",
  bundle_optimization: "Bundle optimization",
  explanation: "Explanation generation",
  checklist: "Checklist generation",
};

function TraceStep({ step }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <Pressable style={styles.step} onPress={() => setExpanded((v) => !v)}>
      <View style={styles.stepHeader}>
        <Text style={styles.stepTitle}>{STEP_LABELS[step.step_name] || step.step_name}</Text>
        <Text style={typography.small}>{new Date(step.created_at).toLocaleString()}</Text>
      </View>
      {expanded && (
        <View style={{ marginTop: spacing.sm }}>
          <Text style={styles.label}>Input</Text>
          <Text style={styles.pre}>{JSON.stringify(step.input_snapshot, null, 2)}</Text>
          <Text style={styles.label}>Output</Text>
          <Text style={styles.pre}>{JSON.stringify(step.output_snapshot, null, 2)}</Text>
        </View>
      )}
    </Pressable>
  );
}

export default function TraceScreen({ route }) {
  const { citizenId } = route.params;
  const [{ loading, error, steps }, setState] = useState({ loading: true, error: null, steps: null });

  const run = useCallback(() => {
    let cancelled = false;
    setState({ loading: true, error: null, steps: null });
    getTrace(citizenId)
      .then((data) => {
        if (!cancelled) setState({ loading: false, error: null, steps: data.steps });
      })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, error: err, steps: null });
      });
    return () => {
      cancelled = true;
    };
  }, [citizenId]);

  useEffect(() => run(), [run]);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.page}>
        <Text style={typography.h1}>Agent reasoning trace</Text>
        <Text style={[typography.muted, { marginBottom: spacing.md }]}>
          Step-by-step record of what the system computed, for full transparency.
        </Text>

        {loading && <LoadingMessage>Loading trace…</LoadingMessage>}
        {error && <ErrorMessage error={error} onRetry={run} />}
        {steps && steps.length === 0 && <InfoMessage>No evaluation run yet.</InfoMessage>}
        {steps && steps.map((step, i) => <TraceStep step={step} key={i} />)}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  page: { padding: spacing.lg, paddingBottom: spacing.xxl },
  step: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  stepHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  stepTitle: { fontWeight: "700", color: colors.text },
  label: { fontWeight: "700", fontSize: 12.5, color: colors.textMuted, marginTop: spacing.sm },
  pre: {
    fontFamily: "monospace",
    fontSize: 11.5,
    color: colors.text,
    backgroundColor: colors.neutralBg,
    borderRadius: radius.md,
    padding: spacing.sm,
    marginTop: 4,
  },
});
