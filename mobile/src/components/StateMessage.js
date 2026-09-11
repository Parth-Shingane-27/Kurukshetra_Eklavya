import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import Button from "./Button";
import { isNetworkError } from "../lib/api";
import { colors, radius, spacing } from "../theme";

export function LoadingMessage({ children }) {
  return (
    <View style={styles.base}>
      <ActivityIndicator size="small" color={colors.textMuted} style={{ marginRight: spacing.sm }} />
      <Text style={styles.text}>{children}</Text>
    </View>
  );
}

export function ErrorMessage({ error, children, onRetry }) {
  const isNetwork = error != null && isNetworkError(error);
  const text = children ?? (isNetwork ? "Connection lost, please retry." : error?.message);
  return (
    <View style={[styles.base, styles.error]}>
      <Text style={[styles.text, styles.errorText]}>{text}</Text>
      {onRetry && <Button title="Retry" variant="secondary" onPress={onRetry} style={{ marginTop: spacing.sm }} />}
    </View>
  );
}

export function InfoMessage({ children }) {
  return (
    <View style={styles.base}>
      <Text style={styles.text}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.neutralBg,
    marginBottom: spacing.md,
  },
  text: { fontSize: 14, color: colors.text, flexShrink: 1 },
  error: { backgroundColor: colors.dangerBg },
  errorText: { color: colors.danger },
});
