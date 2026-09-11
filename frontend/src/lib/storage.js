const KEY = "asbo.citizen_id";

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
  } catch {
    /* ignore */
  }
}
