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
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
