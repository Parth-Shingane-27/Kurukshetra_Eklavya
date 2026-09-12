import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerAccount } from "../api/client";
import { SelectField, TextField } from "../components/FormField";
import { ErrorMessage } from "../components/StateMessage";

const ROLE_OPTIONS = [
  { value: "citizen", label: "Citizen" },
  { value: "admin", label: "Scheme Data Curator (Admin)" },
];

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", role: "citizen", adminBootstrapCredential: "" });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await registerAccount({
        email: form.email.trim(),
        password: form.password,
        role: form.role,
        adminBootstrapCredential: form.adminBootstrapCredential.trim(),
      });
      navigate("/login");
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page">
      <div className="page-header">
        <h1>Create an account</h1>
        <p>Use your email and a password to sign in.</p>
      </div>

      <form className="card" onSubmit={handleSubmit}>
        <TextField label="Email" name="email" type="email" required value={form.email} onChange={handleChange} />
        <TextField
          label="Password"
          name="password"
          type="password"
          required
          value={form.password}
          onChange={handleChange}
          hint="At least 8 characters"
        />
        <SelectField label="Account type" name="role" value={form.role} onChange={handleChange} options={ROLE_OPTIONS} />
        {form.role === "admin" && (
          <TextField
            label="Admin bootstrap credential"
            name="adminBootstrapCredential"
            type="password"
            required
            value={form.adminBootstrapCredential}
            onChange={handleChange}
            hint="Provided by whoever deployed this instance — prevents open self-service admin signup."
          />
        )}

        {error && <ErrorMessage error={error} />}

        <div className="actions">
          <button type="submit" disabled={submitting}>
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </div>
        <p className="hint">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </main>
  );
}
