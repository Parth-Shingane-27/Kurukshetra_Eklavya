// Mirrors the color tokens and spacing scale in frontend/src/index.css so the mobile app
// and the website read as the same product.

export const colors = {
  text: "#172b3a",
  textMuted: "#66757f",
  bg: "#f6f3ed",
  surface: "#fffefa",
  border: "#e2e0d9",
  accent: "#1f7a4d",
  accentSoft: "#e6f4ea",
  accentContrast: "#fffefa",
  danger: "#a94a45",
  dangerBg: "#f7e8e5",
  warning: "#b77928",
  warningBg: "#f7eedb",
  success: "#1f7a4d",
  successBg: "#e6f4ea",
  neutralBg: "#eceae4",
};

export const badgeColors = {
  eligible: { fg: colors.success, bg: colors.successBg },
  held: { fg: colors.success, bg: colors.successBg },
  not_eligible: { fg: colors.danger, bg: colors.dangerBg },
  indeterminate: { fg: colors.warning, bg: colors.warningBg },
  missing: { fg: colors.warning, bg: colors.warningBg },
};

export const badgeLabels = {
  eligible: "Eligible",
  not_eligible: "Not eligible",
  indeterminate: "Needs more info",
  held: "Held",
  missing: "Missing",
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };

export const radius = { md: 10, lg: 16, pill: 999 };

export const shadow = {
  shadowColor: "#141820",
  shadowOffset: { width: 0, height: 4 },
  shadowOpacity: 0.08,
  shadowRadius: 12,
  elevation: 3,
};

export const typography = {
  h1: { fontSize: 26, fontWeight: "700", color: colors.text },
  h2: { fontSize: 19, fontWeight: "700", color: colors.text },
  body: { fontSize: 15, color: colors.text },
  muted: { fontSize: 14, color: colors.textMuted },
  small: { fontSize: 12.5, color: colors.textMuted },
};
