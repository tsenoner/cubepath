import { expect, test } from "@playwright/test";

/**
 * The PWA promise, verified: after one visit, the entire app — pages,
 * 3D players, and fresh scramble generation — works with the network gone.
 */
test("offline: full app works in airplane mode after first visit", async ({ page, context }) => {
  // First (online) visit: let the service worker install and take control.
  await page.goto("/");
  await page.waitForFunction(async () => {
    const reg = await navigator.serviceWorker?.getRegistration();
    return !!reg?.active;
  }, undefined, { timeout: 30_000 });

  // Warm the lazy chunks once (players + scramble worker load on demand,
  // but everything they need is precached — this visit proves the toast path).
  await expect(page.getByTestId("scramble")).toHaveText(/^([RLUDFB][2']? )+[RLUDFB][2']?$/, {
    timeout: 30_000,
  });

  // Airplane mode — and abort any service-worker-originated network request:
  // Playwright's setOffline does not intercept SW fetches (playwright#2311),
  // so without this the test could false-pass by silently hitting the server.
  await context.setOffline(true);
  await context.route("**/*", (route) => {
    if (route.request().serviceWorker()) return route.abort();
    return route.continue();
  });
  await page.reload();

  // Page served by the service worker.
  await expect(page.locator("h2").first()).toContainText("T-Perm", { timeout: 15_000 });

  // Fresh scramble generated fully offline.
  await expect(page.getByTestId("scramble")).toHaveText(/^([RLUDFB][2']? )+[RLUDFB][2']?$/, {
    timeout: 30_000,
  });
  const first = await page.getByTestId("scramble").textContent();
  await page.getByRole("button", { name: "New scramble" }).click();
  await expect(page.getByTestId("scramble")).not.toHaveText(first!, { timeout: 30_000 });

  // Players still render offline.
  const shots = await page.evaluate(async () => {
    const players = [...document.querySelectorAll("twisty-player")] as any[];
    return Promise.all(players.map((p) => p.experimentalScreenshot({ width: 32, height: 32 })));
  });
  expect(shots).toHaveLength(2);
  for (const s of shots) expect(s).toMatch(/^data:image\/png;base64,/);
});
