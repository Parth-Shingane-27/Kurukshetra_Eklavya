import * as Speech from "expo-speech";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Modal, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { WebView } from "react-native-webview";
import Button from "../components/Button";
import { explainFormText, originOf, validateAssistanceSession } from "../lib/api";
import { colors, radius, spacing } from "../theme";

// Injected into the application page's own DOM (not our app's JS) — the only thing it does is
// watch for a text selection and relay it to the native side over the standard WebView
// message bridge. It does NOT continuously capture the page, does not read form values the
// user hasn't selected, and does not run unless this screen is actually showing that page
// (Section 8: "Do not continuously record the page").
const SELECTION_BRIDGE_JS = `
(function () {
  document.addEventListener('selectionchange', function () {
    var text = (window.getSelection() || {}).toString();
    if (text && text.trim().length > 0) {
      window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'selection', text: text.trim() }));
    }
  });
  true;
})();
`;

export default function ApplicationWebViewScreen({ route }) {
  const { applicationUrl, sessionId, schemeName } = route.params;
  const webviewRef = useRef(null);

  const [sessionState, setSessionState] = useState({ status: "validating", token: null, reason: null });
  const [selectedText, setSelectedText] = useState(null);
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState(null);
  const [explainError, setExplainError] = useState(null);

  const origin = originOf(applicationUrl);

  useEffect(() => {
    let cancelled = false;
    validateAssistanceSession(sessionId, origin)
      .then((res) => {
        if (cancelled) return;
        if (res.valid) {
          setSessionState({ status: "active", token: res.assistance_token, reason: null });
        } else {
          setSessionState({ status: "inactive", token: null, reason: res.reason });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSessionState({ status: "inactive", token: null, reason: "Could not verify assistance for this page." });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, origin]);

  const handleMessage = useCallback((event) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === "selection" && data.text) {
        setSelectedText(data.text);
        setExplanation(null);
        setExplainError(null);
      }
    } catch {
      // Ignore malformed bridge messages rather than crash the WebView host screen.
    }
  }, []);

  async function handleExplain() {
    if (!selectedText || sessionState.status !== "active") return;
    setExplaining(true);
    setExplainError(null);
    try {
      const result = await explainFormText({
        assistanceToken: sessionState.token,
        origin,
        selected_text: selectedText,
        explanation_mode: "text_and_voice",
      });
      setExplanation(result);
    } catch (err) {
      setExplainError(err.message || "Could not generate an explanation.");
    } finally {
      setExplaining(false);
    }
  }

  function playVoice() {
    if (!explanation) return;
    const spoken = [explanation.question_meaning, explanation.what_information_is_expected, explanation.important_caution]
      .filter(Boolean)
      .join(". ");
    Speech.stop();
    Speech.speak(spoken);
  }

  return (
    <View style={styles.container}>
      <WebView
        ref={webviewRef}
        source={{ uri: applicationUrl }}
        injectedJavaScript={SELECTION_BRIDGE_JS}
        onMessage={handleMessage}
        style={styles.webview}
      />

      {sessionState.status === "inactive" && (
        <View style={styles.inactiveBanner}>
          <Text style={styles.inactiveText}>
            Form assistance is not available here: {sessionState.reason || "this page is not a supported scheme application."}
          </Text>
        </View>
      )}

      {sessionState.status === "active" && selectedText && (
        <View style={styles.helpBar}>
          <Text style={styles.helpBarText} numberOfLines={1}>
            Selected: "{selectedText}"
          </Text>
          <Button title={explaining ? "Explaining…" : "Explain this"} onPress={handleExplain} disabled={explaining} />
        </View>
      )}

      <Modal visible={!!explanation || !!explainError} transparent animationType="slide" onRequestClose={() => setExplanation(null)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{schemeName}</Text>
              <TouchableOpacity onPress={() => { setExplanation(null); setExplainError(null); }}>
                <Text style={styles.close}>✕</Text>
              </TouchableOpacity>
            </View>
            {explaining && <ActivityIndicator color={colors.accent} />}
            {explainError && <Text style={styles.error}>{explainError}</Text>}
            {explanation && (
              <ScrollView>
                <Text style={styles.label}>What this means</Text>
                <Text style={styles.body}>{explanation.question_meaning}</Text>
                {explanation.what_information_is_expected && (
                  <>
                    <Text style={styles.label}>What to enter</Text>
                    <Text style={styles.body}>{explanation.what_information_is_expected}</Text>
                  </>
                )}
                {explanation.option_explanations?.length > 0 && (
                  <>
                    <Text style={styles.label}>Options</Text>
                    {explanation.option_explanations.map((o, i) => (
                      <Text key={i} style={styles.body}>
                        • {o.option}: {o.meaning}
                      </Text>
                    ))}
                  </>
                )}
                {explanation.example && (
                  <>
                    <Text style={styles.label}>Example</Text>
                    <Text style={styles.body}>{explanation.example}</Text>
                  </>
                )}
                {explanation.important_caution && (
                  <>
                    <Text style={styles.label}>Please note</Text>
                    <Text style={[styles.body, styles.caution]}>{explanation.important_caution}</Text>
                  </>
                )}
                <Button title="🔊 Play" variant="secondary" onPress={playVoice} style={{ marginTop: spacing.md }} />
              </ScrollView>
            )}
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  webview: { flex: 1 },
  inactiveBanner: { backgroundColor: colors.warningBg, padding: spacing.sm },
  inactiveText: { color: colors.warning, fontSize: 12.5 },
  helpBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing.sm,
    padding: spacing.sm,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  helpBarText: { flex: 1, fontSize: 12.5, color: colors.textMuted },
  modalOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.4)", justifyContent: "flex-end" },
  modalSheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    padding: spacing.lg,
    maxHeight: "75%",
  },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.sm },
  modalTitle: { fontSize: 16, fontWeight: "700", color: colors.text },
  close: { fontSize: 18, color: colors.textMuted },
  label: { fontSize: 12.5, fontWeight: "700", color: colors.textMuted, marginTop: spacing.md },
  body: { fontSize: 14, color: colors.text, marginTop: 2 },
  caution: { color: colors.warning },
  error: { color: colors.danger, fontSize: 13 },
});
