import { getToken } from "../auth/session";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status, fieldErrors) {
    super(message);
    this.status = status;
    // Structured {loc, msg} entries from a pydantic 422 (empty for a manually-raised
    // HTTPException, which only ever has a plain string detail) — lets a form map an error
    // back to the specific field/row that caused it, per plan.md Section 17/21's "field-level
    // error" and "rule-field-level error" requirements.
    this.fieldErrors = fieldErrors || [];
  }
}

// A raw network failure (backend unreachable, connection dropped) surfaces as fetch()
// rejecting with a plain TypeError, never as an ApiError — this is exactly how plan.md
// Section 21's "Network failure (frontend <-> backend)" row is distinguished from a real
// API-level error response.
export function isNetworkError(error) {
  return !(error instanceof ApiError);
}

// FastAPI's `detail` is a plain string for a manually-raised HTTPException, but a list of
// structured {loc, msg, ...} objects for an automatic pydantic validation error (422).
function formatErrorDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((e) => `${(e.loc || []).join(".")}: ${e.msg}`).join("; ");
  }
  return null;
}

async function request(path, options = {}) {
  const { headers: customHeaders, ...rest } = options;
  const token = getToken();
  const authHeader = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: { "Content-Type": "application/json", ...authHeader, ...customHeaders },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = formatErrorDetail(body.detail) || `Request failed with status ${res.status}`;
    const fieldErrors = Array.isArray(body.detail) ? body.detail : [];
    throw new ApiError(message, res.status, fieldErrors);
  }
  return res.json();
}

function post(path, body, headers) {
  return request(path, { method: "POST", body: JSON.stringify(body), headers });
}

function put(path, body, headers) {
  return request(path, { method: "PUT", body: JSON.stringify(body), headers });
}

export function adminHeaders(token) {
  return token ? { "X-Admin-Token": token } : {};
}

// FR-016 — two-step (email+password+OTP) authentication.
export function registerAccount({ email, password, role, adminBootstrapCredential }) {
  return post("/api/auth/register", {
    email,
    password,
    role,
    admin_bootstrap_credential: adminBootstrapCredential || undefined,
  });
}

export function loginStep1(email, password) {
  return post("/api/auth/login", { email, password });
}

export function verifyOtpStep2(pendingToken, code) {
  return post("/api/auth/verify-otp", { pending_token: pendingToken, code });
}

export function getMe() {
  return request("/api/auth/me");
}

export function getHealth() {
  return request("/health");
}

export function listSchemes({ includeInactive = false } = {}) {
  const query = includeInactive ? "?include_inactive=true" : "";
  return request(`/api/schemes${query}`);
}

export function getScheme(schemeId) {
  return request(`/api/schemes/${schemeId}`);
}

export function createScheme(scheme, adminToken) {
  return post("/api/schemes", scheme, adminHeaders(adminToken));
}

export function updateScheme(schemeId, patch, adminToken) {
  return put(`/api/schemes/${schemeId}`, patch, adminHeaders(adminToken));
}

export function listConflictRules() {
  return request("/api/conflict-rules");
}

export function createConflictRule(conflictRule, adminToken) {
  return post("/api/conflict-rules", conflictRule, adminHeaders(adminToken));
}

export function createCitizen(profile) {
  return post("/api/citizens", profile);
}

export function getCitizen(citizenId) {
  return request(`/api/citizens/${citizenId}`);
}

export function declareDocuments(citizenId, documents) {
  return post(`/api/citizens/${citizenId}/documents`, { documents });
}

export function evaluateEligibility(citizenId) {
  return post("/api/eligibility/evaluate", { citizen_id: citizenId });
}

export function optimizeBundle(citizenId) {
  return post("/api/bundle/optimize", { citizen_id: citizenId });
}

export function detectConflicts(citizenId) {
  return post("/api/conflicts/detect", { citizen_id: citizenId });
}

export function getBundle(bundleId) {
  return request(`/api/bundle/${bundleId}`);
}

export function generateChecklist(bundleId) {
  return post("/api/checklist/generate", { bundle_id: bundleId });
}

export function getTrace(citizenId) {
  return request(`/api/agent/trace/${citizenId}`);
}

// Context-Aware Form Assistance — mints the short-lived session the browser extension /
// mobile toggle validates before it will activate on the application page (see ApplyLink.jsx).
export function createAssistanceSession(schemeId) {
  return post("/api/assistance/session", { scheme_id: schemeId });
}
