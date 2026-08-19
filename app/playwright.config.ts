import { defineConfig } from "@playwright/test";

// Let route/network handling see service-worker-originated requests.
process.env.PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS = "1";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 1,
  use: {
    baseURL: "http://localhost:4321",
  },
  webServer: {
    command: "npm run preview",
    port: 4321,
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
