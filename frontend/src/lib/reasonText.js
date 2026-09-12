// Turns the rule engine's deterministic (backend + local ruleMatch.js mirror) reason messages
// into plain language for citizens. The engine's `message` is built for traceability/tests
// ("Requires occupation = 'farmer'; profile has 'Student' - did not match.") — useful on the
// reasoning-trace/audit view, but reads like raw internal query output everywhere a citizen
// sees it. This rewrites the same fixed set of message shapes without needing a backend change
// or an LLM call per reason.

const FIELD_LABELS = {
  occupation: "occupation",
  employment_status: "employment status",
  annual_income: "annual income",
  land_holding_acres: "land holding (acres)",
  family_size: "family size",
  marital_status: "marital status",
  bpl_status: "BPL status",
  disability_status: "disability status",
  education_level: "education level",
  social_category: "social category",
  gender: "gender",
  age: "age",
  state: "state",
  district: "district",
};

const OPERATOR_VERBS = {
  "=": "be",
  "<": "be less than",
  "<=": "be at most",
  ">": "be more than",
  ">=": "be at least",
  in: "be one of",
};

function fieldLabel(field) {
  return FIELD_LABELS[field] || field.replace(/_/g, " ");
}

function parseEngineValue(raw) {
  const s = raw.trim();
  if (s === "True" || s === "true") return true;
  if (s === "False" || s === "false") return false;
  if (s === "None" || s === "null") return null;
  if (s.startsWith("[") && s.endsWith("]")) {
    try {
      return JSON.parse(s.replace(/'/g, '"'));
    } catch {
      return s;
    }
  }
  if ((s.startsWith("'") && s.endsWith("'")) || (s.startsWith('"') && s.endsWith('"'))) {
    return s.slice(1, -1);
  }
  const num = Number(s);
  if (s !== "" && !Number.isNaN(num)) return num;
  return s;
}

function formatValue(v) {
  if (v === true) return "Yes";
  if (v === false) return "No";
  if (v === null || v === undefined) return "not provided";
  if (Array.isArray(v)) return v.join(" or ");
  return String(v);
}

// Matches both the backend's `_describe()` ("profile has") and the frontend ruleMatch.js
// mirror's `describe()` ("you have") wording for the same underlying rule check.
const RULE_RE = /^Requires (\S+) (=|<=|<|>=|>|in) (.+?); (?:profile has|you have) (.+?) - (matched|did not match)\.$/;
const MISSING_BACKEND_RE = /^Required field '(\S+)' is missing from the citizen profile\.$/;
const MISSING_FRONTEND_RE = /^Set '(\S+)' in filters to check this scheme\.$/;

export function humanizeReason(reason) {
  const msg = reason?.message || "";

  const ruleMatch = msg.match(RULE_RE);
  if (ruleMatch) {
    const [, field, operator, expectedRaw, actualRaw, result] = ruleMatch;
    const label = fieldLabel(field);
    const expected = formatValue(parseEngineValue(expectedRaw));
    const actual = formatValue(parseEngineValue(actualRaw));
    const verb = OPERATOR_VERBS[operator] || operator;
    if (result === "matched") {
      return `Meets the requirement: ${label} must ${verb} ${expected} — your profile shows ${actual}.`;
    }
    return `Doesn't match yet: ${label} must ${verb} ${expected}, but your profile shows ${actual}.`;
  }

  const missingMatch = msg.match(MISSING_BACKEND_RE) || msg.match(MISSING_FRONTEND_RE);
  if (missingMatch) {
    return `Add your ${fieldLabel(missingMatch[1])} to check this scheme.`;
  }

  return msg;
}
