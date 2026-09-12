import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { converseIntake } from "../api/client";
import AppShell from "../components/layout/AppShell";
import { ErrorMessage, InfoMessage } from "../components/StateMessage";
import { setStoredCitizenId } from "../lib/storage";

const LANGUAGE_OPTIONS = [
  { value: "", label: "Auto-detect" },
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi" },
  { value: "mr", label: "Marathi" },
];

// Maps our language codes to BCP-47 tags the Web Speech API expects.
const SPEECH_LANG_TAGS = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };

function getSpeechRecognitionCtor() {
  return typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;
}

// FR-012 — Multilingual Conversational & Voice Profile Intake. Speech capture is entirely
// client-side (Web Speech API) and purely additive: unsupported browsers, denied mic
// permission, or a recognition error all fall back to the always-available text input —
// never a dead end (NFR-012).
export default function ConversationalIntake() {
  const navigate = useNavigate();
  const [language, setLanguage] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi! Tell me a bit about yourself — for example, your name, age, and where you live — and I'll fill out your profile as we go.",
    },
  ]);
  const [collectedProfile, setCollectedProfile] = useState({});
  const [rejectedFields, setRejectedFields] = useState({});
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [listening, setListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [speechError, setSpeechError] = useState(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    setSpeechSupported(Boolean(getSpeechRecognitionCtor()));
  }, []);

  function startListening() {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return;
    setSpeechError(null);
    const recognition = new Ctor();
    recognition.lang = SPEECH_LANG_TAGS[language] || "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript;
      setInput((prev) => (prev ? `${prev} ${text}` : text));
    };
    recognition.onerror = () => {
      setSpeechError("Voice input didn't work — please type your message instead.");
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    setListening(true);
    recognition.start();
  }

  function stopListening() {
    recognitionRef.current?.stop();
    setListening(false);
  }

  async function handleSend(e) {
    e.preventDefault();
    const transcript = input.trim();
    if (!transcript || sending) return;
    setSending(true);
    setError(null);
    setMessages((m) => [...m, { role: "citizen", text: transcript }]);
    setInput("");
    try {
      const result = await converseIntake({ transcript, sessionId, targetLanguage: language || undefined });
      setSessionId(result.session_id);
      setCollectedProfile(result.collected_profile);
      setRejectedFields(result.rejected_fields);
      setMessages((m) => [...m, { role: "assistant", text: result.assistant_message }]);
      if (result.is_complete && result.citizen_id) {
        setStoredCitizenId(result.citizen_id);
      }
    } catch (err) {
      setError(err);
    } finally {
      setSending(false);
    }
  }

  const profileEntries = Object.entries(collectedProfile);
  const isComplete = ["name", "date_of_birth", "state", "district"].every((f) => collectedProfile[f]);

  return (
    <AppShell
      active="assistant"
      title="AI Assistant"
      subtitle="Talk or type in English, Hindi, or Marathi — no forms to fill in one field at a time."
      meta={<a href="/onboarding">Prefer a structured form instead? Use the step-by-step form →</a>}
    >
      <div className="card">
        <label>
          Language
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            {LANGUAGE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="card catalog-list">
        {messages.map((m, i) => (
          <div key={i} className={`scheme-row ${m.role === "citizen" ? "" : "hint"}`}>
            <div>
              <strong>{m.role === "citizen" ? "You" : "Assistant"}:</strong> {m.text}
            </div>
          </div>
        ))}
      </div>

      {profileEntries.length > 0 && (
        <div className="card">
          <p className="hint">Understood so far — check this is correct:</p>
          <ul className="reasons">
            {profileEntries.map(([field, value]) => (
              <li key={field}>
                <strong>{field.replace(/_/g, " ")}</strong>: {String(value)}
              </li>
            ))}
          </ul>
          {Object.keys(rejectedFields).length > 0 && (
            <ul className="reasons">
              {Object.entries(rejectedFields).map(([field, msg]) => (
                <li key={field} className="field-error">
                  Couldn&apos;t understand <strong>{field.replace(/_/g, " ")}</strong>: {msg}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error && <ErrorMessage error={error} />}

      <form className="card" onSubmit={handleSend}>
        <div className="form-grid">
          <input
            type="text"
            placeholder="Type your message…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={sending}
          />
        </div>
        <div className="actions">
          <button type="submit" disabled={sending || !input.trim()}>
            {sending ? "Sending…" : "Send"}
          </button>
          {speechSupported && (
            <button type="button" className="secondary" onClick={listening ? stopListening : startListening}>
              {listening ? "Stop listening" : "🎤 Speak instead"}
            </button>
          )}
        </div>
        {speechError && <InfoMessage>{speechError}</InfoMessage>}
      </form>

      {isComplete && (
        <div className="card">
          <InfoMessage>Your profile is complete — see your eligible schemes.</InfoMessage>
          <div className="actions">
            <button type="button" onClick={() => navigate("/dashboard")}>
              Go to my dashboard →
            </button>
          </div>
        </div>
      )}
    </AppShell>
  );
}
