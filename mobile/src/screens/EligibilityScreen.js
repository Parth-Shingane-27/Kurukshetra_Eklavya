import { useCallback, useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import StatusBadge from "../components/StatusBadge";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { evaluateEligibility } from "../lib/api";
import { colors, radius, spacing, typography } from "../theme";

export default function EligibilityScreen({ route }) {
  const { citizenId } = route.params;
  const [{ loading, error, results }, setState] = useState({ loading: true, error: null, results: null });

  const run = useCallback(() => {
    let cancelled = false;
    setState({ loading: true, error: null, results: null });
    evaluateEligibility(citizenId)
      .then((data) => {
        if (!cancelled) setState({ loading: false, error: null, results: data.results });
      })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, error: err, results: null });
      });
    return () => {
      cancelled = true;
    };
  }, [citizenId]);

  useEffect(() => run(), [run]);

  const hasEligible = !!results && results.some((r) => r.status === "eligible");

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.page}>
        <Text style={typography.h1}>Your eligible schemes</Text>
        <Text style={[typography.muted, { marginBottom: spacing.md }]}>
          We checked your profile against every active scheme in the knowledge base.
        </Text>

        {loading && <LoadingMessage>Evaluating your profile…</LoadingMessage>}

        {error && error.status === 409 && (
          <ErrorMessage onRetry={run}>
            We couldn&apos;t evaluate any scheme with the information you gave us — every scheme
            needs at least one more field than you provided.
          </ErrorMessage>
        )}
        {error && error.status !== 409 && <ErrorMessage error={error} onRetry={run} />}

        {results && !hasEligible && <InfoMessage>No schemes matched — consider updating your profile with more details.</InfoMessage>}

        {results &&
          results.map((r) => (
            <View style={styles.row} key={r.scheme_id}>
              <View style={styles.rowTop}>
                <Text style={styles.rowTitle}>{r.scheme_name}</Text>
                <StatusBadge status={r.status} />
              </View>
              {r.reasons.length > 0 && (
                <View style={{ marginTop: 4 }}>
                  {r.reasons.map((reason, i) => (
                    <Text key={i} style={styles.reason}>
                      • {reason.message}
                    </Text>
                  ))}
                </View>
              )}
            </View>
          ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  page: { padding: spacing.lg, paddingBottom: spacing.xxl },
  row: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  rowTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", gap: spacing.sm },
  rowTitle: { fontWeight: "700", color: colors.text, flexShrink: 1 },
  reason: { fontSize: 13, color: colors.textMuted, marginBottom: 2 },
});
