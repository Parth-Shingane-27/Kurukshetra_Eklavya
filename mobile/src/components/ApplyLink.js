import { useState } from "react";
import { Linking, StyleSheet, Text, TouchableOpacity } from "react-native";
import { createAssistanceSession } from "../lib/api";
import { colors, spacing } from "../theme";

const STATUS_COPY = {
  verified: { label: "Apply on the official portal ↗", note: null, color: colors.success },
  unverified: {
    label: "Visit application page ↗",
    note: "This link has not been independently verified — check the address carefully before entering personal details.",
    color: colors.warning,
  },
  not_available: {
    label: null,
    note: "Online application is not available for this scheme. Please follow the official offline application process.",
    color: colors.textMuted,
  },
  state_specific: {
    label: null,
    note: "The application process varies by state/department — check with your local office for the correct portal.",
    color: colors.textMuted,
  },
};

const ASSISTABLE_STATUSES = new Set(["verified", "unverified"]);

// Mirrors web's ApplyLink.jsx. When `navigation` and `schemeId` are both supplied, opens the
// application inside our own in-app WebView (ApplicationWebViewScreen) rather than the
// external system browser — only an in-app WebView gives the assistance overlay a JS
// injection point (Section 14: an external browser can't be read/controlled by the app).
// Without both, falls back to the plain external-browser open (no assistance available there).
export default function ApplyLink({ url, status, moreInfoUrl, schemeId, schemeName, navigation }) {
  const copy = STATUS_COPY[status] || STATUS_COPY.unverified;
  const [opening, setOpening] = useState(false);

  async function handlePress() {
    if (schemeId && navigation && ASSISTABLE_STATUSES.has(status)) {
      setOpening(true);
      try {
        const session = await createAssistanceSession(schemeId);
        navigation.navigate("ApplicationWebView", {
          applicationUrl: url,
          sessionId: session.session_id,
          schemeName,
        });
      } catch {
        Linking.openURL(url);
      } finally {
        setOpening(false);
      }
      return;
    }
    Linking.openURL(url);
  }

  if (!url) {
    if (!copy.note) return null;
    return (
      <>
        <Text style={[styles.note, { color: copy.color }]}>{copy.note}</Text>
        {moreInfoUrl && (
          <TouchableOpacity onPress={() => Linking.openURL(moreInfoUrl)}>
            <Text style={styles.link}>More information ↗</Text>
          </TouchableOpacity>
        )}
      </>
    );
  }

  return (
    <>
      <TouchableOpacity onPress={handlePress} disabled={opening}>
        <Text style={[styles.link, { color: copy.color }]}>{opening ? "Opening…" : copy.label}</Text>
      </TouchableOpacity>
      {copy.note && <Text style={[styles.note, { color: copy.color }]}>{copy.note}</Text>}
      {ASSISTABLE_STATUSES.has(status) && schemeId && navigation && (
        <Text style={styles.note}>Form help will be available inside the app.</Text>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  link: { fontSize: 13.5, fontWeight: "700", marginTop: spacing.xs },
  note: { fontSize: 12, marginTop: 2, color: colors.textMuted },
});
