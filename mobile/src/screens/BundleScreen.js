import { useCallback, useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Button from "../components/Button";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { detectConflicts, getScheme, optimizeBundle } from "../lib/api";
import { colors, radius, spacing, typography } from "../theme";

export default function BundleScreen({ route, navigation }) {
  const { citizenId } = route.params;
  const [{ loading, error, bundle, schemes, conflicts }, setState] = useState({
    loading: true,
    error: null,
    bundle: null,
    schemes: [],
    conflicts: [],
  });

  const run = useCallback(() => {
    let cancelled = false;
    setState({ loading: true, error: null, bundle: null, schemes: [], conflicts: [] });
    (async () => {
      try {
        const conflictData = await detectConflicts(citizenId);
        const bundleData = await optimizeBundle(citizenId);
        const schemeDetails = await Promise.all(bundleData.scheme_ids.map((id) => getScheme(id)));
        if (!cancelled) {
          setState({ loading: false, error: null, bundle: bundleData, schemes: schemeDetails, conflicts: conflictData.conflicts });
        }
      } catch (err) {
        if (!cancelled) setState({ loading: false, error: err, bundle: null, schemes: [], conflicts: [] });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [citizenId]);

  useEffect(() => run(), [run]);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.page}>
        <Text style={typography.h1}>Your optimized bundle</Text>
        <Text style={[typography.muted, { marginBottom: spacing.md }]}>
          The best conflict-free combination of schemes for your profile.
        </Text>

        {loading && <LoadingMessage>Checking for conflicts and optimizing your bundle…</LoadingMessage>}
        {error && <ErrorMessage error={error} onRetry={run} />}

        {bundle && bundle.scheme_ids.length === 0 && (
          <InfoMessage>No viable bundle — none of the schemes you&apos;re eligible for could be included.</InfoMessage>
        )}

        {bundle && schemes.length > 0 && (
          <View style={styles.card}>
            <Text style={typography.h2}>Recommended schemes</Text>
            <Text style={styles.total}>₹{bundle.total_benefit_value.toLocaleString()}</Text>
            <Text style={typography.muted}>total estimated benefit</Text>
            {schemes.map((s) => (
              <View style={styles.line} key={s.id}>
                <Text style={styles.lineTitle}>{s.name}</Text>
                <Text style={typography.small}>
                  ₹{s.benefit_value_estimate.toLocaleString()} · {s.category}
                </Text>
              </View>
            ))}
          </View>
        )}

        {conflicts.length > 0 && (
          <View style={styles.card}>
            <Text style={typography.h2}>Conflicts detected</Text>
            {conflicts.map((c, i) => (
              <View style={styles.line} key={i}>
                <Text style={styles.lineTitle}>
                  {c.scheme_a_name} vs. {c.scheme_b_name}
                </Text>
                <Text style={typography.small}>{c.reason}</Text>
              </View>
            ))}
          </View>
        )}

        {bundle && bundle.excluded.length > 0 && (
          <View style={styles.card}>
            <Text style={typography.h2}>Excluded from your bundle</Text>
            {bundle.excluded.map((e) => (
              <View style={styles.line} key={e.scheme_id}>
                <Text style={styles.lineTitle}>{e.scheme_name}</Text>
                <Text style={typography.small}>{e.reason}</Text>
              </View>
            ))}
          </View>
        )}

        {bundle && bundle.explanation_text && (
          <View style={styles.card}>
            <Text style={typography.h2}>Why this bundle</Text>
            <Text style={styles.explanation}>{bundle.explanation_text}</Text>
          </View>
        )}

        {bundle && bundle.bundle_id && (
          <Button
            title="View my checklist →"
            onPress={() => navigation.navigate("Checklist", { bundleId: bundle.bundle_id, citizenId })}
            style={{ marginTop: spacing.sm }}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  page: { padding: spacing.lg, paddingBottom: spacing.xxl },
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  total: { fontSize: 22, fontWeight: "800", color: colors.accent, marginTop: 4 },
  line: { paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.border, marginTop: 8 },
  lineTitle: { fontWeight: "700", color: colors.text },
  explanation: { color: colors.text, lineHeight: 20, marginTop: 4 },
});
