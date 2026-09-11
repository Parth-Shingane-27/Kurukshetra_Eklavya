# ASBO Demo Script

Three sample citizen profiles, each verified live against the current seed knowledge base
(`database/seed_schemes.json`, 8 schemes). Together they rehearse every distinct behavior the
system needs to demonstrate: both conflict mechanisms (BR-004 and BR-005), all three
eligibility statuses, and all three checklist document states. Re-verify after any change to
`seed_schemes.json` — the exact field values below are load-bearing, not illustrative.

Before each run: clear `citizens`, `eligibility_results`, `bundles`, `agent_audit_logs` (leave
`schemes`/`conflict_rules` seeded) so citizen IDs and the Trace screen start clean.

---

## Profile 1 — Sunita Kadam: multiple eligible schemes + group conflict (BR-005)

**Profile Intake form:**
| Field | Value |
|---|---|
| Name | Sunita Kadam |
| Date of birth | 1975-04-20 |
| State | Maharashtra |
| District | Nashik |
| Occupation | farmer |
| Land holding (acres) | 3 |
| BPL status | Yes |
| Annual household income | 200000 |
| Documents held | *(none checked)* |

**Expected — Eligible Schemes:** PM-KISAN (eligible), National Old Age Pension (not eligible —
age 51 < 60), Pradhan Mantri Awas Yojana / PMAY (eligible), State Rural Housing (eligible), the
remaining 4 schemes indeterminate (missing fields not provided).

**Expected — Bundle:** PMAY (₹130,000) + PM-KISAN (₹6,000) = **₹136,000 total**. State Rural
Housing excluded — "same conflict group as 'Pradhan Mantri Awas Yojana (Rural)'" (demonstrates
BR-005: shared `conflict_group`, optimizer picks the higher-value scheme).

**Expected — Checklist:** all 5 required documents show **Missing** (Aadhaar Card, Land
Ownership Record, Bank Passbook, BPL Ration Card, Land Ownership Proof) — demonstrates the
"citizen declared no documents → everything missing" case (FR-008).

---

## Profile 2 — Arjun Verma: direct pairwise conflict (BR-004) + partially-held documents

**Profile Intake form:**
| Field | Value |
|---|---|
| Name | Arjun Verma |
| Date of birth | 2000-06-15 |
| State | Uttar Pradesh |
| District | Lucknow |
| Employment status | Unemployed |
| Education level | Undergraduate |
| Documents held | Aadhaar Card, Education Certificate |

**Expected — Eligible Schemes:** Skill Development Training Stipend (eligible), State
Unemployment Allowance Scheme (eligible), the other 6 indeterminate.

**Expected — Bundle:** Unemployment Allowance (₹18,000) wins; Skill Development Stipend
excluded — "mutually exclusive with 'State Unemployment Allowance Scheme'" (demonstrates
BR-004: an explicitly declared `conflict_rules` pair, distinct from Profile 1's group
mechanism).

**Expected — Checklist:** Aadhaar Card and Education Certificate show **Held**; Employment
Exchange Registration and Bank Passbook show **Missing** — demonstrates a partially-complete
document set (distinct from Profile 1's all-missing and Profile 3's all-held).

---

## Profile 3 — Rajesh Kumar: single clean eligibility, no conflict, nothing missing

**Profile Intake form:**
| Field | Value |
|---|---|
| Name | Rajesh Kumar |
| Date of birth | 1990-01-01 |
| State | Kerala |
| District | Kochi |
| Occupation | salaried |
| Land holding (acres) | 0 |
| Disability status | Yes |
| BPL status | No |
| Annual household income | 900000 |
| Social category | General |
| Education level | Postgraduate |
| Employment status | Employed |
| Documents held | Aadhaar Card, Disability Certificate, Bank Passbook |

**Expected — Eligible Schemes:** Disability Pension Scheme (eligible); all other 7 schemes
**not eligible** (fully resolved — every field the rule engine needs is provided, so nothing
comes back indeterminate). Demonstrates the "definitively not eligible, reason named" case
distinctly from Profiles 1–2's indeterminate results.

**Expected — Bundle:** Disability Pension only, ₹9,600 total, no exclusions (no conflict
declared for this scheme).

**Expected — Checklist:** all 3 required documents show **Held** — "No documents missing."

---

## Full rehearsal checklist

- [ ] Profile 1 walkthrough: Profile Intake → Eligible Schemes → Bundle (conflicts detected +
      excluded sections both populated) → Checklist (all missing) → Trace (5 steps, in order)
- [ ] Profile 2 walkthrough: same path, confirm the *different* conflict type/reason text and
      the partially-held checklist
- [ ] Profile 3 walkthrough: confirm the "No documents missing" checklist empty state and the
      absence of a "Conflicts detected" / "Excluded" section on the Bundle screen
- [ ] Admin screen: log in with the admin token, deactivate a scheme, confirm it drops out of
      a fresh Eligible Schemes run, reactivate it
- [ ] Confirm no browser console errors across all screens (see `tests/frontend/*.spec.js` for
      the automated version of this walkthrough)
