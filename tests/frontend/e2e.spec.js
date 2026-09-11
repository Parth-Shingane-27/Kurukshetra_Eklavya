// End-to-end demo journey (Section 22): profile -> eligible -> conflicts -> bundle ->
// explanation -> checklist -> trace, against a seeded sample citizen and scheme set.
//
// Prerequisites (not started by this test): MongoDB reachable, backend running on :8000
// (which seeds database/seed_schemes.json on startup), frontend dev server on :5173.
// Run with: npx playwright test

import { expect, test } from "@playwright/test";

test("full citizen journey: profile -> eligible -> bundle -> checklist -> trace", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Tell us about yourself")).toBeVisible();

  // A profile deliberately shaped to be eligible for two schemes that share a
  // conflict_group (pmay_housing vs state_housing_subsidy) — exercises FR-005/FR-006 together
  // with FR-004, not just the happy path of a single uncontested eligible scheme.
  await page.fill("#name", "Asha Patil");
  await page.fill("#date_of_birth", "1975-04-20");
  await page.fill("#state", "Maharashtra");
  await page.fill("#district", "Nashik");
  await page.selectOption("#bpl_status", "true");
  await page.fill("#annual_income", "200000");
  await page.fill("#occupation", "farmer");
  await page.fill("#land_holding_acres", "3");
  await page.getByRole("button", { name: "Find my schemes" }).click();

  await expect(page.getByText("Your eligible schemes")).toBeVisible();
  await expect(page.getByText("PM-KISAN Samman Nidhi")).toBeVisible();
  await expect(page.locator(".badge-eligible").first()).toBeVisible();

  await page.getByRole("button", { name: /See my optimized bundle/ }).click();

  await expect(page.getByText("Your optimized bundle")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Conflicts detected" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Excluded from your bundle" })).toBeVisible();
  await expect(page.getByText("State Rural Housing Assistance Scheme").first()).toBeVisible();
  await expect(page.locator(".explanation")).not.toBeEmpty();

  await page.getByRole("button", { name: /View my checklist/ }).click();

  await expect(page.getByText("Your application checklist")).toBeVisible();
  const aadhaarRow = page.locator(".checklist-item", { hasText: "Aadhaar Card" });
  await expect(aadhaarRow).toContainText("PM-KISAN Samman Nidhi");
  await expect(aadhaarRow).toContainText("Pradhan Mantri Awas Yojana (Rural)");

  await page.getByRole("button", { name: /View reasoning trace/ }).click();

  await expect(page.getByText("Agent reasoning trace")).toBeVisible();
  await expect(page.locator("details.trace-step")).toHaveCount(5);
  const stepNames = await page.locator("details.trace-step summary span").allInnerTexts();
  expect(stepNames.filter((_, i) => i % 2 === 0)).toEqual([
    "Eligibility evaluation",
    "Conflict detection",
    "Bundle optimization",
    "Explanation generation",
    "Checklist generation",
  ]);
});
