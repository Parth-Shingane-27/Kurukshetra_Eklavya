// Admin Scheme KB screen (FR-011, Section 17's Admin screen). Same prerequisites as
// e2e.spec.js: MongoDB reachable, backend on :8000, frontend preview build on :4173.
// ADMIN_TOKEN defaults to backend/.env's ADMIN_CREDENTIAL ("change-me-admin-token");
// override with E2E_ADMIN_TOKEN if that's been changed.
//
// The Admin screen's old manual "paste a shared token" field was replaced with real
// email+password login. This test registers + logs in via the backend API directly (covered
// end-to-end by its own suite in tests/backend/test_auth.py) and seeds the resulting session
// into localStorage before loading the page — this test is about the Admin scheme-CRUD UI, not
// re-proving login works.

import { expect, request as pwRequest, test } from "@playwright/test";

const ADMIN_TOKEN = process.env.E2E_ADMIN_TOKEN || "change-me-admin-token";
const API_BASE_URL = process.env.E2E_API_BASE_URL || "http://localhost:8000";
const SCHEME_NAME = `E2E Test Scheme ${Date.now()}`;
const ADMIN_EMAIL = `e2e_admin_${Date.now()}@example.com`;
const ADMIN_PASSWORD = "s3cret-pass-e2e";

async function loginAsAdmin(api) {
  await api.post("/api/auth/register", {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD, role: "admin", admin_bootstrap_credential: ADMIN_TOKEN },
  });
  const loginRes = await api.post("/api/auth/login", { data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD } });
  return loginRes.json();
}

test("admin can create a scheme and toggle it inactive/active", async ({ page }) => {
  const api = await pwRequest.newContext({ baseURL: API_BASE_URL });
  const { access_token, user } = await loginAsAdmin(api);

  await page.goto("/admin");
  await page.evaluate(
    ({ token, user }) => {
      localStorage.setItem("asbo_access_token", token);
      localStorage.setItem("asbo_user", JSON.stringify(user));
    },
    { token: access_token, user }
  );
  await page.reload();

  await expect(page.getByText("Scheme knowledge base admin")).toBeVisible();
  await expect(page.getByText(/Logged in as/).first()).toBeVisible();

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
