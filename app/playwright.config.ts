import { defineConfig } from "@playwright/test";

// Let route/network handling see service-worker-originated requests.
process.env.PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS = "1";

// A parallel `astro dev` on the default port would be reused by
// `reuseExistingServer`, and the dev toolbar injects its own <h1> elements —
// which breaks every heading assertion for reasons that have nothing to do
// with the app. Allow the port to be moved out of the way.
const PORT = Number(process.env.PW_PORT ?? 4321);

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 1,
  use: {
    baseURL: `http://localhost:${PORT}`,
  },
  webServer: {
    command: `npm run preview -- --port ${PORT}`,
    port: PORT,
    // `astro preview` daemonizes itself when it detects a coding agent in the
    // environment (astro/dist/cli/agent.js), so the command Playwright spawns
    // exits immediately and the run dies with "Process from config.webServer
    // exited early." Any value for this env var turns that detection off, and
    // only the `--background` flag can re-enable it — so this pins the server
    // to the foreground without changing anything in CI, where astro sees no
    // agent and stayed in the foreground already.
    env: { ASTRO_PREVIEW_BACKGROUND: "0" },
    // Locally, attach to a preview server that is already up. In CI that would
    // silently test a stale server instead of the dist/ just built.
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
