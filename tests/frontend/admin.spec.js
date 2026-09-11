// Admin Scheme KB screen (FR-011, Section 17's Admin screen). Same prerequisites as
// e2e.spec.js: MongoDB reachable, backend on :8000, frontend preview build on :4173.
// ADMIN_TOKEN defaults to backend/.env's ADMIN_CREDENTIAL ("change-me-admin-token");
// override with E2E_ADMIN_TOKEN if that's been changed.

import { expect, test } from "@playwright/test";

const ADMIN_TOKEN = process.env.E2E_ADMIN_TOKEN || "change-me-admin-token";
const SCHEME_NAME = `E2E Test Scheme ${Date.now()}`;

test("admin can create a scheme and toggle it inactive/active", async ({ page }) => {
  await page.goto("/admin");
  await expect(page.getByText("Scheme knowledge base admin")).toBeVisible();

  await page.fill("#admin_token", ADMIN_TOKEN);

  await page.fill("#name", SCHEME_NAME);
  await page.fill("#category", "Social welfare & Empowerment");
  await page.fill("#benefit_type", "cash_transfer");
  await page.fill("#benefit_value_estimate", "12345");

  await page.getByRole("button", { name: "+ Add rule" }).click();
  await page.fill('input[name="rule_field_0"]', "marital_status");
  await page.selectOption('select[name="rule_operator_0"]', "=");
  await page.fill('input[name="rule_value_0"]', "widowed");

  await page.getByRole("button", { name: "Create scheme" }).click();

  const schemeRow = page.locator(".scheme-row", { hasText: SCHEME_NAME });
  await expect(schemeRow).toBeVisible({ timeout: 10000 });
  await expect(schemeRow).toContainText("₹12,345");

  await schemeRow.getByRole("button", { name: "Deactivate" }).click();
  await expect(schemeRow.getByRole("button", { name: "Reactivate" })).toBeVisible();

  await schemeRow.getByRole("button", { name: "Reactivate" }).click();
  await expect(schemeRow.getByRole("button", { name: "Deactivate" })).toBeVisible();
});
