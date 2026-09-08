/// <reference types="vitest/config" />
import { getViteConfig } from "astro/config";

/**
 * Astro's own Vite config, so `.astro` components can be rendered inside a
 * test. That is not a convenience: the three-tier stickering ladder shipped
 * broken because every test exercised `maskFor` directly while the component
 * called it with one argument fewer, so the suite has to be able to assert on
 * what the COMPONENT emits, not only on what the helper returns.
 */
export default getViteConfig({
  test: {
    include: ["tests/**/*.spec.ts"],
    // Syncs the content collection into the store this (serve-mode) config
    // reads; without it `getCollection()` is `[]` on a fresh checkout.
    globalSetup: ["tests/global-setup.ts"],
    testTimeout: 30000,
  },
});
