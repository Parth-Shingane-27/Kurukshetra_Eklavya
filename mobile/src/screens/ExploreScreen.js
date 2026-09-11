import { useEffect, useMemo, useState } from "react";
import { FlatList, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import FilterSheet from "../components/FilterSheet";
import SchemeCard from "../components/SchemeCard";
import { ErrorMessage, InfoMessage, LoadingMessage } from "../components/StateMessage";
import { useCitizen } from "../context/CitizenContext";
import { listSchemes } from "../lib/api";
import { boolToTriState, toBoolOrUndefined } from "../lib/profileFields";
import { computeAge, evaluateSchemeAgainstFilters } from "../lib/ruleMatch";
import { colors, radius, spacing, typography } from "../theme";

function filtersFromCitizen(citizen) {
  return {
    state: citizen.state || "",
    occupation: citizen.occupation || "",
    employment_status: citizen.employment_status || "",
    education_level: citizen.education_level || "",
    social_category: citizen.social_category || "",
    marital_status: citizen.marital_status || "",
    gender: citizen.gender || "",
    bpl_status: boolToTriState(citizen.bpl_status),
    disability_status: boolToTriState(citizen.disability_status),
    age: citizen.date_of_birth ? String(computeAge(citizen.date_of_birth)) : "",
    annual_income: citizen.annual_income != null ? String(citizen.annual_income) : "",
    land_holding_acres: citizen.land_holding_acres != null ? String(citizen.land_holding_acres) : "",
  };
}

const EMPTY_FILTERS = {
  state: "",
  occupation: "",
  employment_status: "",
  education_level: "",
  social_category: "",
  marital_status: "",
  gender: "",
  bpl_status: "",
  disability_status: "",
  age: "",
  annual_income: "",
  land_holding_acres: "",
};

function normalizeFilters(filters) {
  const num = (v) => (v !== "" && v != null ? Number(v) : undefined);
  return {
    state: filters.state || undefined,
    occupation: filters.occupation || undefined,
    employment_status: filters.employment_status || undefined,
    education_level: filters.education_level || undefined,
    social_category: filters.social_category || undefined,
    marital_status: filters.marital_status || undefined,
    gender: filters.gender || undefined,
    bpl_status: toBoolOrUndefined(filters.bpl_status),
    disability_status: toBoolOrUndefined(filters.disability_status),
    age: num(filters.age),
    annual_income: num(filters.annual_income),
    land_holding_acres: num(filters.land_holding_acres),
  };
}

const STATUS_RANK = { eligible: 0, indeterminate: 1, not_eligible: 2 };

export default function ExploreScreen({ navigation }) {
  const { citizen } = useCitizen();
  const [allSchemes, setAllSchemes] = useState([]);
  const [schemesError, setSchemesError] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [profileDefaults, setProfileDefaults] = useState(EMPTY_FILTERS);
  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    if (!citizen) return;
    const defaults = filtersFromCitizen(citizen);
    setFilters(defaults);
    setProfileDefaults(defaults);
  }, [citizen]);

  useEffect(() => {
    listSchemes()
      .then(setAllSchemes)
      .catch((err) => setSchemesError(err));
  }, []);

  function handleFieldChange(name, value) {
    setFilters((f) => ({ ...f, [name]: value }));
  }

  const hasFilterChanges = useMemo(() => JSON.stringify(filters) !== JSON.stringify(profileDefaults), [filters, profileDefaults]);

  const exploreResults = useMemo(() => {
    const normalized = normalizeFilters(filters);
    const q = searchText.trim().toLowerCase();
    return allSchemes
      .map((scheme) => {
        const { status, reasons } = evaluateSchemeAgainstFilters(scheme, normalized);
        return { scheme, status, reasons };
      })
      .filter(({ scheme }) => {
        if (!q) return true;
        const haystack = [scheme.name, scheme.description, scheme.category, scheme.issuing_authority].filter(Boolean).join(" ").toLowerCase();
        return haystack.includes(q);
      })
      .sort((a, b) => STATUS_RANK[a.status] - STATUS_RANK[b.status]);
  }, [allSchemes, filters, searchText]);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.header}>
        <Text style={typography.h1}>Explore schemes</Text>
        <Text style={typography.muted}>Search the full catalogue or try different filter values.</Text>
      </View>

      <FlatList
        data={exploreResults}
        keyExtractor={({ scheme }) => scheme.id}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <>
            <TextInput
              style={styles.search}
              placeholder="Search by name, category, or department…"
              placeholderTextColor="#9aa0ab"
              value={searchText}
              onChangeText={setSearchText}
            />
            <FilterSheet
              filters={filters}
              onFieldChange={handleFieldChange}
              onReset={() => setFilters(profileDefaults)}
              onClear={() => setFilters(EMPTY_FILTERS)}
              hasChanges={hasFilterChanges}
            />
            {schemesError && <ErrorMessage error={schemesError} />}
            {allSchemes.length === 0 && !schemesError && <LoadingMessage>Loading scheme catalogue…</LoadingMessage>}
          </>
        }
        renderItem={({ item }) => (
          <SchemeCard scheme={item.scheme} matchStatus={item.status} reasons={item.reasons} navigation={navigation} />
        )}
        ListEmptyComponent={allSchemes.length > 0 ? <InfoMessage>No schemes match your search.</InfoMessage> : null}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: { padding: spacing.lg, paddingBottom: 0 },
  list: { padding: spacing.lg, paddingBottom: spacing.xxl },
  search: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    paddingVertical: 10,
    paddingHorizontal: 14,
    backgroundColor: colors.surface,
    marginBottom: spacing.md,
    fontSize: 15,
    color: colors.text,
  },
});
