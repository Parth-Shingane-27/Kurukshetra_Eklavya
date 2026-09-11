import { useCallback, useEffect, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Button from "../components/Button";
import SchemeCard from "../components/SchemeCard";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { useCitizen } from "../context/CitizenContext";
import { detectConflicts, evaluateEligibility, getScheme, optimizeBundle } from "../lib/api";
import { clearStoredCitizenId } from "../lib/storage";
import { colors, radius, spacing, typography } from "../theme";

export default function HomeScreen({ navigation }) {
  const { citizen, citizenId, error: citizenError, reload: reloadCitizen } = useCitizen();
  const [personalized, setPersonalized] = useState({ loading: true, error: null, bundle: null, schemes: [], eligibleCount: null });
  const [refreshing, setRefreshing] = useState(false);

  const loadPersonalized = useCallback(() => {
    if (!citizenId) return undefined;
    let cancelled = false;
    setPersonalized({ loading: true, error: null, bundle: null, schemes: [], eligibleCount: null });
    (async () => {
      try {
        const eligibility = await evaluateEligibility(citizenId);
        const eligibleCount = eligibility.results.filter((r) => r.status === "eligible").length;
        await detectConflicts(citizenId);
        const bundle = await optimizeBundle(citizenId);
        const schemes = await Promise.all(bundle.scheme_ids.map((id) => getScheme(id)));
        if (!cancelled) setPersonalized({ loading: false, error: null, bundle, schemes, eligibleCount });
      } catch (err) {
        if (!cancelled) setPersonalized({ loading: false, error: err, bundle: null, schemes: [], eligibleCount: null });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [citizenId]);

  useEffect(() => loadPersonalized(), [loadPersonalized]);

  async function handleRefresh() {
    setRefreshing(true);
    loadPersonalized();
    setRefreshing(false);
  }

  async function handleSwitchProfile() {
    await clearStoredCitizenId();
    navigation.getParent()?.reset({ index: 0, routes: [{ name: "Landing" }] });
  }

  if (citizenError) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.page}>
          <ErrorMessage error={citizenError} onRetry={reloadCitizen}>
            We couldn&apos;t load your profile. It may no longer exist.
          </ErrorMessage>
          <Button title="Start over" onPress={handleSwitchProfile} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.topbar}>
        <Text style={styles.brand}>ASBO</Text>
        <View style={styles.topbarActions}>
          {citizen && <Text style={typography.muted}>Hi, {citizen.name.split(" ")[0]}</Text>}
          <Button title="Switch" variant="ghost" onPress={handleSwitchProfile} />
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.page}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={colors.accent} />}
      >
        <Text style={typography.h1}>Your recommended bundle</Text>
        <Text style={[typography.muted, { marginBottom: spacing.md }]}>
          Based on the profile you gave us — pull to refresh.
        </Text>

        {personalized.loading && <LoadingMessage>Evaluating your profile…</LoadingMessage>}

        {personalized.error && personalized.error.status === 409 && (
          <ErrorMessage onRetry={loadPersonalized}>
            None of our schemes could be evaluated with what you&apos;ve told us so far — add a few
            more details to your profile to get a match.
          </ErrorMessage>
        )}
        {personalized.error && personalized.error.status !== 409 && (
          <ErrorMessage error={personalized.error} onRetry={loadPersonalized} />
        )}

        {personalized.bundle && (
          <>
            <View style={styles.stats}>
              <View style={styles.statTile}>
                <Text style={styles.statValue}>{personalized.eligibleCount}</Text>
                <Text style={styles.statLabel}>Eligible schemes</Text>
              </View>
              <View style={styles.statTile}>
                <Text style={styles.statValue}>₹{personalized.bundle.total_benefit_value.toLocaleString()}</Text>
                <Text style={styles.statLabel}>Bundle value</Text>
              </View>
              <View style={styles.statTile}>
                <Text style={styles.statValue}>{personalized.bundle.excluded.length}</Text>
                <Text style={styles.statLabel}>Excluded</Text>
              </View>
            </View>

            {personalized.schemes.length === 0 && (
              <InfoMessage>No viable bundle yet — none of your eligible schemes could be included.</InfoMessage>
            )}

            {personalized.schemes.map((s) => (
              <SchemeCard key={s.id} scheme={s} matchStatus="eligible" />
            ))}

            <View style={styles.actions}>
              <Button
                title="Full eligibility breakdown →"
                variant="secondary"
                onPress={() => navigation.navigate("Eligibility", { citizenId })}
              />
              <Button
                title="Bundle & conflicts →"
                variant="secondary"
                onPress={() => navigation.navigate("Bundle", { citizenId })}
              />
              {personalized.bundle.bundle_id && (
                <Button
                  title="Application checklist →"
                  onPress={() => navigation.navigate("Checklist", { bundleId: personalized.bundle.bundle_id, citizenId })}
                />
              )}
              <Button title="Reasoning trace →" variant="ghost" onPress={() => navigation.navigate("Trace", { citizenId })} />
            </View>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  topbar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  brand: { fontWeight: "800", color: colors.accent, letterSpacing: 0.6 },
  topbarActions: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  page: { padding: spacing.lg, paddingBottom: spacing.xxl },
  stats: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.md },
  statTile: {
    flex: 1,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.md,
  },
  statValue: { fontSize: 19, fontWeight: "800", color: colors.accent },
  statLabel: { fontSize: 11.5, color: colors.textMuted, marginTop: 2 },
  actions: { gap: spacing.sm, marginTop: spacing.sm },
});
