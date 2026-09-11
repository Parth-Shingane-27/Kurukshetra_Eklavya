import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "asbo.citizen_id";

export async function getStoredCitizenId() {
  try {
    return await AsyncStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export async function setStoredCitizenId(citizenId) {
  try {
    await AsyncStorage.setItem(KEY, citizenId);
  } catch {
    /* storage unavailable — session still works, just won't persist */
  }
}

export async function clearStoredCitizenId() {
  try {
    await AsyncStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
