// End-to-end demo journey (Section 22): landing -> onboarding -> personalized dashboard ->
// full eligibility breakdown -> bundle -> checklist -> trace, against a seeded sample citizen
// and scheme set.
//
// Prerequisites (not started by this test): MongoDB reachable, backend running on :8000
// (which seeds database/seed_schemes.json on startup), frontend dev server on :5173.
// Run with: npx playwright test
//
// Rewritten for the Landing/Onboarding/Dashboard restructuring — profile intake is no longer
// the root route; "/" is a marketing Landing page that hands off to a multi-step Onboarding
// wizard, which lands the citizen on a personalized Dashboard rather than directly on the
// Eligible Schemes screen.

import { expect, test } from "@playwright/test";

test("full citizen journey: landing -> onboarding -> dashboard -> bundle -> checklist -> trace", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Find every scheme you qualify for/ })).toBeVisible();
  await page.getByRole("button", { name: "Get started" }).click();

  // Step 1: the essentials (required fields only).
  await expect(page.getByText("The essentials")).toBeVisible();
  await page.fill("#name", "Asha Patil");
  await page.fill("#date_of_birth", "1975-04-20");
  await page.fill("#state", "Maharashtra");
  await page.fill("#district", "Nashik");
  await page.getByRole("button", { name: "Continue" }).click();

  // Step 2: household & work — deliberately shaped to be eligible for two schemes that share
  // a conflict_group (pmay_housing vs state_housing_subsidy), exercising FR-005/FR-006
  // together with FR-004, not just the happy path of a single uncontested eligible scheme.
  await expect(page.getByText("Household & work")).toBeVisible();
  await page.fill("#occupation", "farmer");
  await page.fill("#annual_income", "200000");
  await page.fill("#land_holding_acres", "3");
  await page.getByRole("button", { name: "Continue" }).click();

  // Step 3: about you.
  await expect(page.getByText("About you")).toBeVisible();
  await page.selectOption("#bpl_status", "true");
  await page.getByRole("button", { name: "Continue" }).click();

  // Step 4: documents (none held) — submits and lands on the personalized Dashboard.
  await expect(page.getByText("Documents you already have")).toBeVisible();
  await page.getByRole("button", { name: "Find my schemes" }).click();

  await expect(page.getByRole("heading", { name: "Your recommended bundle" })).toBeVisible();
  await expect(page.getByText("PM-KISAN Samman Nidhi")).toBeVisible();

  await page.getByRole("button", { name: /Full eligibility breakdown/ }).click();

  await expect(page.getByText("Your eligible schemes")).toBeVisible();
  await expect(page.getByText("PM-KISAN Samman Nidhi")).toBeVisible();
  await expect(page.locator(".badge-eligible").first()).toBeVisible();

  await page.getByRole("button", { name: /See my optimized bundle/ }).click();

  await expect(page.getByText("Your optimized bundle")).toBeVisible();
  // Explanation generation calls the LLM (BR-010 falls back to a template on failure/timeout,
  // but a slow/rate-limited provider can still take a while to give up) — allow more time here
  // than the suite default before asserting the bundle actually finished computing.
  await expect(page.getByRole("heading", { name: "Conflicts detected" })).toBeVisible({ timeout: 20000 });
  await expect(page.getByRole("heading", { name: "Excluded from your bundle" })).toBeVisible();
  await expect(page.getByText("State Rural Housing Assistance Scheme").first()).toBeVisible();
  await expect(page.locator(".explanation")).not.toBeEmpty();

  await page.getByRole("button", { name: /View my checklist/ }).click();

  await expect(page.getByText("Your application checklist")).toBeVisible();
  const aadhaarRow = page.locator(".checklist-item", { hasText: "Aadhaar Card" });
  await expect(aadhaarRow).toBeVisible({ timeout: 15000 });
  await expect(aadhaarRow).toContainText("PM-KISAN Samman Nidhi");
  await expect(aadhaarRow).toContainText("Pradhan Mantri Awas Yojana (Rural)");

  await page.getByRole("button", { name: /View reasoning trace/ }).click();

  await expect(page.getByText("Agent reasoning trace")).toBeVisible();
  await expect(page.locator("details.trace-step").first()).toBeVisible({ timeout: 15000 });
  // Exact count of 5, not 9: Dashboard's "recommended bundle" section computes
  // eligibility/conflicts/bundle/explanation once, and forwards those results via router
  // `state` to EligibleSchemes -> Bundle -> (their "See my optimized bundle"/nav buttons) so
  // neither screen silently re-runs (and re-logs) the same computation when reached from
  // Dashboard. Direct navigation (a bookmark, a refresh) still fetches fresh, unaffected.
  await expect(page.locator("details.trace-step")).toHaveCount(5);
  const allSpanTexts = await page.locator("details.trace-step summary span").allInnerTexts();
  const stepNames = allSpanTexts.filter((_, i) => i % 2 === 0); // each summary: [label, timestamp]
  expect(stepNames).toEqual([
      "Eligibility evaluation",
      "Conflict detection",
      "Bundle optimization",
      "Explanation generation",
      "Checklist generation",
  ]);
});
