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
  if (res.status === 204) return null;
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

export function registerAccount({ email, password, role, adminBootstrapCredential }) {
  return post("/api/auth/register", {
    email,
    password,
    role,
    admin_bootstrap_credential: adminBootstrapCredential || undefined,
  });
}

export function login(email, password) {
  return post("/api/auth/login", { email, password });
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

export function updateCitizen(citizenId, patch) {
  return put(`/api/citizens/${citizenId}`, patch);
}

export function declareDocuments(citizenId, documents) {
  return post(`/api/citizens/${citizenId}/documents`, { documents });
}

// Plain document management (upload/list/download) — not verification. Storing an actual
// file for a document type also auto-marks it "held" on the profile server-side.
export function uploadDocument(citizenId, { documentType, filename, contentType, fileBase64 }) {
  return post(`/api/citizens/${citizenId}/document-uploads`, {
    document_type: documentType,
    filename,
    content_type: contentType,
    file_base64: fileBase64,
  });
}

export function listUploadedDocuments(citizenId) {
  return request(`/api/citizens/${citizenId}/document-uploads`);
}

export function deleteUploadedDocument(citizenId, uploadId) {
  return request(`/api/citizens/${citizenId}/document-uploads/${uploadId}`, { method: "DELETE" });
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

// FR-013 — Quick Scheme Eligibility Checker. No auth, no citizen record (BR-014).
export function quickCheck(schemeId, criteria) {
  return post("/api/quick-check", { scheme_id: schemeId, criteria });
}

// FR-014 — Scheme Catalog Search with Form-Filling Guides. Public, no auth.
export function searchCatalog({ query, category, state } = {}) {
  const params = new URLSearchParams();
  if (query) params.set("query", query);
  if (category) params.set("category", category);
  if (state) params.set("state", state);
  const qs = params.toString();
  return request(`/api/catalog/schemes${qs ? `?${qs}` : ""}`);
}

export function getSchemeGuide(schemeId) {
  return request(`/api/catalog/schemes/${schemeId}/guide`);
}

// Form Guide — YouTube tutorial recommendation. Fetched lazily, only when a citizen opens a
// scheme's guide; never blocks or slows the Form Guide itself.
export function getVideoTutorial(schemeId) {
  return request(`/api/catalog/schemes/${schemeId}/video-tutorial`);
}

// Public, citizen-independent scheme deadline lookup (see backend/app/modules/scheme_deadline).
export function getSchemeDeadline(schemeId) {
  return request(`/api/catalog/schemes/${schemeId}/deadline`);
}

export function searchCatalogNaturalLanguage(text) {
  return post("/api/catalog/search-natural-language", { text });
}

export function getAnalytics() {
  return request("/api/admin/analytics");
}

// Citizen-reported scheme data-quality issues (distinct from the RAG candidate queue).
export function createSchemeReport({ schemeId, reason, comment, citizenId }) {
  return post("/api/scheme-reports", { scheme_id: schemeId, reason, comment: comment || undefined, citizen_id: citizenId || undefined });
}

export function listSchemeReports(status) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/scheme-reports${qs}`);
}

export function resolveSchemeReport(reportId, status, adminNotes) {
  return post(`/api/scheme-reports/${reportId}/resolve`, { status, admin_notes: adminNotes || undefined });
}

// FR-015 — RAG-based knowledge base freshness. Admin-only (require_admin).
export function triggerRagRefresh(schemeId) {
  return post(`/api/admin/rag/refresh?scheme_id=${encodeURIComponent(schemeId)}`, {});
}

export function listRagCandidates({ status } = {}) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/admin/rag-candidates${qs}`);
}

export function approveRagCandidate(candidateId) {
  return post(`/api/admin/rag-candidates/${candidateId}/approve`, {});
}

export function rejectRagCandidate(candidateId, reason) {
  return post(`/api/admin/rag-candidates/${candidateId}/reject`, { reason });
}

// New-scheme discovery — live web search (Tavily) for schemes not yet in the catalogue.
// Admin-only (require_admin). Discoveries are proposals only, same review-before-trust
// pipeline as the RAG candidate queue above.
export function searchSchemeDiscovery(query, category) {
  return post("/api/admin/scheme-discovery/search", { query, category: category || undefined });
}

export function listSchemeDiscoveries(status) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/admin/scheme-discoveries${qs}`);
}

export function approveSchemeDiscovery(discoveryId) {
  return post(`/api/admin/scheme-discoveries/${discoveryId}/approve`, {});
}

export function rejectSchemeDiscovery(discoveryId, reason) {
  return post(`/api/admin/scheme-discoveries/${discoveryId}/reject`, { reason });
}

// FR-012 — Multilingual Conversational & Voice Profile Intake.
export function converseIntake({ transcript, sessionId, targetLanguage }) {
  return post("/api/intake/converse", {
    transcript,
    session_id: sessionId || undefined,
    target_language: targetLanguage || undefined,
  });
}

// Feedback / Grievance — internal platform ticketing, never an official government submission.
export function createGrievance({ citizenId, category, description, schemeId }) {
  return post("/api/grievances", { citizen_id: citizenId, category, description, scheme_id: schemeId || undefined });
}

export function listGrievancesForCitizen(citizenId) {
  return request(`/api/grievances/citizen/${citizenId}`);
}

export function listAllGrievances(status) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/grievances${qs}`);
}

export function resolveGrievance(grievanceId, resolutionNote) {
  return post(`/api/grievances/${grievanceId}/resolve`, { resolution_note: resolutionNote });
}

// Fraud Detection — admin-only internal trust-and-safety review queue.
export function listAllFraudFlags({ riskLevel, reviewed } = {}) {
  const params = new URLSearchParams();
  if (riskLevel) params.set("risk_level", riskLevel);
  if (reviewed !== undefined) params.set("reviewed", reviewed);
  const qs = params.toString();
  return request(`/api/fraud${qs ? `?${qs}` : ""}`);
}

export function screenCitizenForFraud(citizenId, schemeId) {
  return post("/api/fraud/screen", { citizen_id: citizenId, scheme_id: schemeId || undefined });
}

export function reviewFraudFlag(flagId, reviewerNotes) {
  return post(`/api/fraud/${flagId}/review`, { reviewer_notes: reviewerNotes });
}

// In-app Notification Center — real events only, no email/push.
export function listNotifications(citizenId) {
  return request(`/api/citizens/${citizenId}/notifications`);
}

export function getUnreadNotificationCount(citizenId) {
  return request(`/api/citizens/${citizenId}/notifications/unread-count`);
}

export function markNotificationRead(citizenId, notificationId) {
  return post(`/api/citizens/${citizenId}/notifications/${notificationId}/read`, {});
}

// Saved/watchlist schemes.
export function saveScheme(citizenId, schemeId) {
  return post(`/api/citizens/${citizenId}/saved-schemes`, { scheme_id: schemeId });
}

export function unsaveScheme(citizenId, schemeId) {
  return request(`/api/citizens/${citizenId}/saved-schemes/${schemeId}`, { method: "DELETE" });
}

export function listSavedSchemes(citizenId) {
  return request(`/api/citizens/${citizenId}/saved-schemes`);
}

// National scheme dataset search (RAG-backed, 3,397 schemes) — distinct from the curated
// scheme catalogue; never asserted as officially verified.
export function searchNationalSchemeDatabase(q) {
  return request(`/api/policy/search?q=${encodeURIComponent(q)}`);
}

// Personalized live web search (Tavily + Gemini) scoped to one citizen's profile — distinct
// from the admin-only scheme-discovery queue; results are shown directly to the citizen,
// always as unverified, never written to the curated scheme catalogue.
export function getWebSchemes(citizenId, { force = false } = {}) {
  return request(`/api/citizens/${citizenId}/web-schemes${force ? "?force=true" : ""}`);
}
