import { defineConfig } from "vitest/config";

// Dev-only configuration for the inline fitting-diagram tests.
// Runs once (no watch mode) via `npm test` -> `vitest run`.
export default defineConfig({
  test: {
    // jsdom gives tests a DOM environment so they can drive the
    // inline diagram controller and its exposed test hook.
    environment: "jsdom",
    include: ["test/**/*.test.js"],
    watch: false,
  },
});
