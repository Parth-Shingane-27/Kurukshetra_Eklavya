import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginStep1, verifyOtpStep2 } from "../api/client";
import { setSession } from "../auth/session";
import { TextField } from "../components/FormField";
import { ErrorMessage } from "../components/StateMessage";

// FR-016 — two-step (email+password+OTP) login. Step 1 verifies email+password and emails a
// one-time code; step 2 verifies that code and issues the access token.
export default function Login() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [pendingToken, setPendingToken] = useState(null);
  const [debugOtp, setDebugOtp] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleStep1(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await loginStep1(email.trim(), password);
      setPendingToken(res.pending_token);
      setDebugOtp(res.debug_otp || null);
      setStep(2);
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleStep2(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await verifyOtpStep2(pendingToken, code.trim());
      setSession(res.access_token, res.user);
      navigate(res.user.role === "admin" ? "/admin" : "/");
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page">
      <div className="page-header">
        <h1>Log in</h1>
        <p>Step {step} of 2 — {step === 1 ? "email & password" : "email verification code"}.</p>
      </div>

      <div className="card">
        {step === 1 && (
          <form onSubmit={handleStep1}>
            <TextField label="Email" name="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            <TextField
              label="Password"
              name="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <ErrorMessage error={error} />}
            <div className="actions">
              <button type="submit" disabled={submitting}>
                {submitting && <span className="spinner" aria-hidden="true" />}
                {submitting ? "Sending code…" : "Continue"}
              </button>
            </div>
          </form>
        )}

        {step === 2 && (
          <form onSubmit={handleStep2}>
            <p className="hint">A 6-digit verification code was emailed to {email}.</p>
            {debugOtp && (
              <p className="hint">
                No email provider configured — for local testing, your code is: <strong>{debugOtp}</strong>
              </p>
            )}
            <TextField
              label="Verification code"
              name="code"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              hint="6 digits"
            />
            {error && <ErrorMessage error={error} />}
            <div className="actions">
              <button type="submit" disabled={submitting}>
                {submitting && <span className="spinner" aria-hidden="true" />}
                {submitting ? "Verifying…" : "Verify & log in"}
              </button>
              <button type="button" className="secondary" onClick={() => setStep(1)}>
                Back
              </button>
            </div>
          </form>
        )}
      </div>
    </main>
  );
}
