import { useCallback, useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Button from "../components/Button";
import StatusBadge from "../components/StatusBadge";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { generateChecklist } from "../lib/api";
import { colors, radius, spacing, typography } from "../theme";

export default function ChecklistScreen({ route, navigation }) {
  const { bundleId, citizenId } = route.params;
  const [{ loading, error, checklist }, setState] = useState({ loading: true, error: null, checklist: null });

  const run = useCallback(() => {
    let cancelled = false;
    setState({ loading: true, error: null, checklist: null });
    generateChecklist(bundleId)
      .then((data) => {
        if (!cancelled) setState({ loading: false, error: null, checklist: data });
      })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, error: err, checklist: null });
      });
    return () => {
      cancelled = true;
    };
  }, [bundleId]);

  useEffect(() => run(), [run]);

  const items = checklist?.checklist_items ?? [];
  const nothingMissing = items.length > 0 && items.every((i) => i.status === "held");

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.page}>
        <Text style={typography.h1}>Your application checklist</Text>
        <Text style={[typography.muted, { marginBottom: spacing.md }]}>
          Everything you need to apply, consolidated across your recommended schemes.
        </Text>

        {loading && <LoadingMessage>Building your checklist…</LoadingMessage>}
        {error && <ErrorMessage error={error} onRetry={run} />}

        {checklist && items.length === 0 && <InfoMessage>No documents are required — there&apos;s nothing to prepare.</InfoMessage>}
        {checklist && nothingMissing && <InfoMessage>No documents missing — you already have everything you need.</InfoMessage>}

        {items.map((item) => (
          <View style={styles.item} key={item.document_type}>
            <View style={{ flexShrink: 1 }}>
              <Text style={styles.itemTitle}>{item.document_type}</Text>
              <Text style={typography.small}>Needed for: {item.related_scheme_names.join(", ")}</Text>
            </View>
            <StatusBadge status={item.status} />
          </View>
        ))}

        {checklist && citizenId && (
          <Button
            title="View reasoning trace →"
            variant="secondary"
            onPress={() => navigation.navigate("Trace", { citizenId })}
            style={{ marginTop: spacing.md }}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  page: { padding: spacing.lg, paddingBottom: spacing.xxl },
  item: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  itemTitle: { fontWeight: "700", color: colors.text },
});
