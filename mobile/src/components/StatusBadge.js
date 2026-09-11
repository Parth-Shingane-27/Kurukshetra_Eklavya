import { StyleSheet, Text, View } from "react-native";
import { badgeColors, badgeLabels, radius } from "../theme";

export default function StatusBadge({ status }) {
  const colors = badgeColors[status] || { fg: "#5b6270", bg: "#eef0f3" };
  return (
    <View style={[styles.badge, { backgroundColor: colors.bg }]}>
      <Text style={[styles.text, { color: colors.fg }]}>{badgeLabels[status] || status}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingVertical: 3,
    paddingHorizontal: 10,
    borderRadius: radius.pill,
    alignSelf: "flex-start",
  },
  text: {
    fontSize: 12,
    fontWeight: "700",
  },
});
