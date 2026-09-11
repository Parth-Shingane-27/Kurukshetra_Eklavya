import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/frontend",
  timeout: 30_000,
  use: {
    // Targets the production preview build (`npm run build && npm run preview`, port 4173) by
    // default — StrictMode's dev-only double-effect-invocation (React, not this app's own
    // logic) would otherwise double every write the journey makes, which is confusing noise
    // for an E2E assertion. Override with E2E_BASE_URL=http://localhost:5173 to run against
    // the dev server instead (e.g. for faster iteration while the assertions are unstable).
    baseURL: process.env.E2E_BASE_URL || "http://localhost:4173",
  },
});
