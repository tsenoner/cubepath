import { expect, test } from "@playwright/test";

const SCRAMBLE_RE = /^([RLUDFB][2']? ){10,}[RLUDFB][2']?$/;

/**
 * The PWA promise, verified: after ONE visit to the home page, the entire
 * site — lessons, 3D players, fresh scrambles — works with the network gone.
 */
test("offline: whole course works in airplane mode after first visit", async ({
  page,
  context,
}) => {
  // Single online visit: the service worker precaches everything.
  await page.goto("/");
  await page.waitForFunction(async () => {
    const reg = await navigator.serviceWorker?.getRegistration();
    return !!reg?.active;
  }, undefined, { timeout: 30_000 });
  // Give workbox a beat to finish precaching all routes.
  await page.waitForFunction(async () => {
    const keys = await caches.keys();
    if (keys.length === 0) return false;
    const cache = await caches.open(keys.find((k) => k.includes("precache")) ?? keys[0]);
    return (await cache.keys()).length > 30;
  }, undefined, { timeout: 30_000 });

  // Airplane mode — and abort any service-worker-originated network request:
  // Playwright's setOffline does not intercept SW fetches (playwright#2311),
  // so without this the test could false-pass by silently hitting the server.
  await context.setOffline(true);
  await context.route("**/*", (route) => {
    if (route.request().serviceWorker()) return route.abort();
    return route.continue();
  });

  // A lesson never visited before renders offline, players included.
  await page.goto("/learn/two-look-oll/");
  await expect(page.locator("h1")).toContainText("Anti-Sune", { timeout: 15_000 });
  const shot = await page.evaluate(async () => {
    const open = document.querySelector("details[open] twisty-player") as any;
    return open?.experimentalScreenshot({ width: 32, height: 32 });
  });
  expect(shot).toMatch(/^data:image\/png;base64,/);

  // Fresh scrambles generate offline on a page never visited before.
  await page.goto("/practice/");
  await expect(page.getByTestId("scramble")).toHaveText(SCRAMBLE_RE, { timeout: 30_000 });
  const first = await page.getByTestId("scramble").textContent();
  await page.getByRole("button", { name: "New scramble" }).click();
  await expect(page.getByTestId("scramble")).not.toHaveText(first!, { timeout: 30_000 });
});
