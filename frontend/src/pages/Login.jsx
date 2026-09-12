import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/client";
import { setSession } from "../auth/session";
import { TextField } from "../components/FormField";
import { ErrorMessage } from "../components/StateMessage";
import { setStoredCitizenId } from "../lib/storage";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await login(email.trim(), password);
      setSession(res.access_token, res.user);
      if (res.user.role === "admin") {
        navigate("/admin");
      } else if (res.user.citizen_id) {
        // Take the citizen straight to their own dashboard, not the generic marketing
        // landing page — a returning user should never have to re-find their profile.
        setStoredCitizenId(res.user.citizen_id);
        navigate("/dashboard");
      } else {
        // No profile linked to this account yet — send them to build one instead of a page
        // that can't show anything personalized for them.
        navigate("/onboarding");
      }
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
        <p>Enter your email and password.</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
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
              {submitting ? "Logging in…" : "Log in"}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}
