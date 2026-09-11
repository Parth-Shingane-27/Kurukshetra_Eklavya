import { ActivityIndicator, Pressable, StyleSheet, Text } from "react-native";
import { colors, radius, spacing } from "../theme";

const VARIANTS = {
  primary: { bg: colors.accent, fg: colors.accentContrast, border: colors.accent },
  secondary: { bg: "transparent", fg: colors.accent, border: colors.accent },
  ghost: { bg: "transparent", fg: colors.textMuted, border: "transparent" },
};

export default function Button({ title, onPress, variant = "primary", disabled, loading, style }) {
  const v = VARIANTS[variant] || VARIANTS.primary;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.base,
        { backgroundColor: v.bg, borderColor: v.border, opacity: disabled ? 0.6 : pressed ? 0.85 : 1 },
        style,
      ]}
    >
      {loading && <ActivityIndicator size="small" color={v.fg} style={{ marginRight: spacing.sm }} />}
      <Text style={[styles.text, { color: v.fg }]}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderRadius: radius.md,
    borderWidth: 1,
  },
  text: {
    fontSize: 15,
    fontWeight: "700",
  },
});
