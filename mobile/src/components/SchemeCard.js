import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import Button from "./Button";
import StatusBadge from "./StatusBadge";
import { colors, radius, shadow, spacing } from "../theme";

export default function SchemeCard({ scheme, matchStatus, reasons }) {
  const [expanded, setExpanded] = useState(false);
  const categories = (scheme.category || "")
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean);

  return (
    <View style={styles.card}>
      <View style={styles.top}>
        <View style={styles.tags}>
          {categories.map((c) => (
            <View key={c} style={styles.tag}>
              <Text style={styles.tagText}>{c}</Text>
            </View>
          ))}
        </View>
        {matchStatus && <StatusBadge status={matchStatus} />}
      </View>

      <Text style={styles.name}>{scheme.name}</Text>
      {scheme.issuing_authority && <Text style={styles.authority}>{scheme.issuing_authority}</Text>}
      {scheme.description && <Text style={styles.desc}>{scheme.description}</Text>}

      <Text style={styles.benefit}>
        ₹{scheme.benefit_value_estimate.toLocaleString()}{" "}
        <Text style={styles.benefitType}>· {scheme.benefit_type.replaceAll("_", " ")}</Text>
      </Text>

      <Button
        title={expanded ? "Hide requirements ▲" : "Requirements & documents ▼"}
        variant="ghost"
        onPress={() => setExpanded((v) => !v)}
        style={styles.detailsToggle}
      />

      {expanded && (
        <View style={styles.details}>
          {reasons && reasons.length > 0 && (
            <View style={{ marginBottom: spacing.sm }}>
              {reasons.map((r, i) => (
                <Text key={i} style={styles.reason}>
                  • {r.message}
                </Text>
              ))}
            </View>
          )}
          {scheme.document_requirements.length > 0 && (
            <>
              <Text style={styles.hint}>Documents needed:</Text>
              {scheme.document_requirements.map((d) => (
                <Text key={d.document_type} style={styles.reason}>
                  • {d.document_type}
                  {!d.is_mandatory && " (optional)"}
                </Text>
              ))}
            </>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
    ...shadow,
  },
  top: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 6, flexShrink: 1 },
  tag: { backgroundColor: colors.accentSoft, borderRadius: radius.pill, paddingVertical: 2, paddingHorizontal: 9 },
  tagText: { fontSize: 11, fontWeight: "700", color: colors.accent },
  name: { fontSize: 16.5, fontWeight: "700", color: colors.text, marginBottom: 2 },
  authority: { fontSize: 12.5, color: colors.textMuted, marginBottom: 6 },
  desc: { fontSize: 14, color: colors.text, marginBottom: 8 },
  benefit: { fontSize: 15, fontWeight: "700", color: colors.accent, marginBottom: 4 },
  benefitType: { fontSize: 13, fontWeight: "500", color: colors.textMuted, textTransform: "capitalize" },
  detailsToggle: { alignSelf: "flex-start", paddingHorizontal: 0, paddingVertical: 4 },
  details: { marginTop: 4, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: spacing.sm },
  hint: { fontSize: 12.5, color: colors.textMuted, marginBottom: 4, fontWeight: "600" },
  reason: { fontSize: 13, color: colors.textMuted, marginBottom: 3 },
});
