// Client-side mirror of backend/app/modules/rule_engine/engine.py's evaluate_scheme —
// AND-within-logical_group / OR-across-groups, same missing-field/priority handling
// (eligible > indeterminate > not_eligible). Used only for the dashboard's exploratory
// "quick match" against arbitrary filter values (not the citizen's saved profile), so
// filter changes get instant feedback without a backend round trip per keystroke. The
// citizen's actual eligibility always comes from the real /api/eligibility/evaluate call.

export function computeAge(dateOfBirth, asOf = new Date()) {
  const dob = new Date(dateOfBirth);
  if (Number.isNaN(dob.getTime())) return undefined;
  const hadBirthday =
    asOf.getMonth() > dob.getMonth() ||
    (asOf.getMonth() === dob.getMonth() && asOf.getDate() >= dob.getDate());
  return asOf.getFullYear() - dob.getFullYear() - (hadBirthday ? 0 : 1);
}

function isPresent(value) {
  return value !== undefined && value !== null && value !== "";
}

function evaluateCondition(operator, actual, expected) {
  switch (operator) {
    case "=":
      return actual === expected;
    case "<":
      return actual < expected;
    case "<=":
      return actual <= expected;
    case ">":
      return actual > expected;
    case ">=":
      return actual >= expected;
    case "in":
      return Array.isArray(expected) && expected.includes(actual);
    default:
      return false;
  }
}

function describe(rule, actual, passed) {
  return {
    field_name: rule.field_name,
    message: `Requires ${rule.field_name} ${rule.operator} ${JSON.stringify(rule.value)}; you have ${JSON.stringify(actual)} - ${passed ? "matched" : "did not match"}.`,
  };
}

export function evaluateSchemeAgainstFilters(scheme, filters) {
  const rules = scheme.rules || [];
  if (rules.length === 0) return { status: "eligible", reasons: [] };

  const context = filters;
  const groups = new Map();
  for (const rule of rules) {
    const key = rule.logical_group ?? null;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(rule);
  }

  const missingFields = new Map();
  let firstFailureReason = null;

  for (const groupRules of groups.values()) {
    const missingInGroup = groupRules
      .filter((r) => !isPresent(context[r.field_name]))
      .map((r) => r.field_name);
    if (missingInGroup.length > 0) {
      missingInGroup.forEach((f) => missingFields.set(f, null));
      continue;
    }

    let groupPassed = true;
    const groupReasons = [];
    for (const rule of groupRules) {
      const actual = context[rule.field_name];
      const passed = evaluateCondition(rule.operator, actual, rule.value);
      const reason = describe(rule, actual, passed);
      groupReasons.push(reason);
      if (!passed) {
        groupPassed = false;
        if (!firstFailureReason) firstFailureReason = reason;
        break;
      }
    }
    if (groupPassed) return { status: "eligible", reasons: groupReasons };
  }

  if (missingFields.size > 0) {
    const reasons = [...missingFields.keys()].map((field_name) => ({
      field_name,
      message: `Set '${field_name}' in filters to check this scheme.`,
    }));
    return { status: "indeterminate", reasons };
  }
  return { status: "not_eligible", reasons: firstFailureReason ? [firstFailureReason] : [] };
}
