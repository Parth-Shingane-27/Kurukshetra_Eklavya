const KEY = "asbo.citizen_id";
const BUNDLE_KEY = "asbo.bundle_id";

export function getStoredCitizenId() {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setStoredCitizenId(citizenId) {
  try {
    localStorage.setItem(KEY, citizenId);
  } catch {
    /* private-browsing / storage disabled — session still works, just won't persist */
  }
}

export function clearStoredCitizenId() {
  try {
    localStorage.removeItem(KEY);
    localStorage.removeItem(BUNDLE_KEY);
  } catch {
    /* ignore */
  }
}

export function getStoredBundleId() {
  try {
    return localStorage.getItem(BUNDLE_KEY);
  } catch {
    return null;
  }
}

export function setStoredBundleId(bundleId) {
  try {
    if (bundleId) localStorage.setItem(BUNDLE_KEY, bundleId);
  } catch {
    /* private-browsing / storage disabled — session still works, just won't persist */
  }
}
