import Constants from "expo-constants";

// In Expo Go, Metro's own dev host is reachable at the same LAN IP the phone used to load the
// bundle — reuse it so the backend doesn't need a hardcoded IP. Falls back to localhost for
// web/simulator runs where the backend is on the same machine.
function resolveDevApiBaseUrl() {
  const hostUri = Constants.expoConfig?.hostUri || Constants.expoConfig?.debuggerHost;
  if (hostUri) {
    const host = hostUri.split(":")[0];
    if (host) return `http://${host}:8000`;
  }
  return "http://localhost:8000";
}

export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL || resolveDevApiBaseUrl();

export class ApiError extends Error {
  constructor(message, status, fieldErrors) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors || [];
  }
}

export function isNetworkError(error) {
  return !(error instanceof ApiError);
}

function formatErrorDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((e) => `${(e.loc || []).join(".")}: ${e.msg}`).join("; ");
  }
  return null;
}

async function request(path, options = {}) {
  const { headers: customHeaders, ...rest } = options;
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: { "Content-Type": "application/json", ...customHeaders },
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

export function getHealth() {
  return request("/health");
}

export function listSchemes() {
  return request("/api/schemes");
}

export function getScheme(schemeId) {
  return request(`/api/schemes/${schemeId}`);
}

export function createCitizen(profile) {
  return post("/api/citizens", profile);
}

export function getCitizen(citizenId) {
  return request(`/api/citizens/${citizenId}`);
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

export function generateChecklist(bundleId) {
  return post("/api/checklist/generate", { bundle_id: bundleId });
}

export function getTrace(citizenId) {
  return request(`/api/agent/trace/${citizenId}`);
}
