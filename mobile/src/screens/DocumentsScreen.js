import { useCallback, useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Button from "../components/Button";
import StatusBadge from "../components/StatusBadge";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { useCitizen } from "../context/CitizenContext";
import { generateChecklist, optimizeBundle } from "../lib/api";
import { colors, radius, spacing, typography } from "../theme";

// "Documents" tab — the tab-bar-reachable equivalent of ChecklistScreen (which stays as a
// separate root-stack screen reachable with an already-known bundleId, e.g. from Home). A tab
// has no bundleId to receive as a param, so this screen computes its own bundle first (the
// checklist is generated per-bundle, not per-citizen) via the same optimizeBundle call
// ApplicationsScreen makes — consistent with how the web Dashboard/Bundle/Checklist pages each
// independently call optimizeBundle rather than sharing one cached result.
export default function DocumentsScreen({ navigation }) {
  const { citizenId } = useCitizen();
  const [{ loading, error, checklist }, setState] = useState({ loading: true, error: null, checklist: null });

  const run = useCallback(() => {
    if (!citizenId) {
      setState({ loading: false, error: null, checklist: null });
      return undefined;
    }
    let cancelled = false;
    setState({ loading: true, error: null, checklist: null });
    (async () => {
      try {
        const bundle = await optimizeBundle(citizenId);
        const data = await generateChecklist(bundle.bundle_id);
        if (!cancelled) setState({ loading: false, error: null, checklist: data });
      } catch (err) {
        if (!cancelled) setState({ loading: false, error: err, checklist: null });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [citizenId]);

  useEffect(() => run(), [run]);

  const items = checklist?.checklist_items ?? [];
  const nothingMissing = items.length > 0 && items.every((i) => i.status === "held");

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.page}>
        <Text style={typography.h1}>Documents</Text>
        <Text style={[typography.muted, { marginBottom: spacing.md }]}>
          Everything you need to apply, consolidated across your recommended schemes.
        </Text>

        {!citizenId && <InfoMessage>Complete your profile first to see your document checklist.</InfoMessage>}

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
