import { StyleSheet, Text, TextInput, View } from "react-native";
import { colors, radius, spacing } from "../theme";

export default function TextField({
  label,
  value,
  onChangeText,
  error,
  hint,
  required,
  keyboardType = "default",
  placeholder,
  autoCapitalize = "sentences",
}) {
  return (
    <View style={styles.field}>
      {label && (
        <Text style={styles.label}>
          {label}
          {required ? " *" : ""}
        </Text>
      )}
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#9aa0ab"
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        style={[styles.input, error ? styles.inputError : null]}
      />
      {hint && !error && <Text style={styles.hint}>{hint}</Text>}
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { marginBottom: spacing.md },
  label: { fontSize: 13.5, fontWeight: "600", color: colors.text, marginBottom: 4 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingVertical: 10,
    paddingHorizontal: 12,
    fontSize: 15,
    color: colors.text,
    backgroundColor: colors.surface,
  },
  inputError: { borderColor: colors.danger },
  hint: { fontSize: 12.5, color: colors.textMuted, marginTop: 4 },
  error: { fontSize: 12.5, color: colors.danger, marginTop: 4 },
});
