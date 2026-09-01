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
  await page.waitForFunction(
    async () => {
      const reg = await navigator.serviceWorker?.getRegistration();
      return !!reg?.active;
    },
    undefined,
    { timeout: 30_000 },
  );
  // Wait for workbox to finish precaching EVERYTHING (the app flags it).
  await page.waitForFunction(
    () => document.documentElement.dataset.offlineReady === "1",
    undefined,
    { timeout: 120_000 },
  );

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
    // twisty-player is a custom element; experimentalScreenshot is cubing.js API.
    const open = document.querySelector("details[open] twisty-player") as
      | (Element & {
          experimentalScreenshot(o: { width: number; height: number }): Promise<string>;
        })
      | null;
    return open?.experimentalScreenshot({ width: 32, height: 32 });
  });
  expect(shot).toMatch(/^data:image\/png;base64,/);

  // EVERY query-string link a lesson offers must survive airplane mode, and the
  // list is DERIVED from the page rather than typed here. A precache lookup
  // matches on the full URL, so a query param the service worker is not told to
  // ignore is simply a different, uncached URL — and with `navigateFallback:
  // null` there is nothing behind the miss. This shipped: all 16
  // `/practice/?group=` buttons, the filled primary call to action on 12
  // lessons, were dead offline, and because that element also carries
  // `data-lesson-advance` an offline reader taking it earned no lesson credit.
  // The bare `/practice/` visit below is why the suite stayed green.
  const queryLinks = await page
    .locator('main a[href*="?"]')
    .evaluateAll((els) =>
      [...new Set(els.map((e) => (e as HTMLAnchorElement).getAttribute("href")!))].filter(Boolean),
    );
  expect(queryLinks.length).toBeGreaterThan(0);
  for (const href of queryLinks) {
    const res = await page.goto(href);
    expect(res?.ok(), `${href} must resolve offline`).toBe(true);
    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });
  }

  // Fresh WCA scrambles generate offline on a page never visited before.
  await page.goto("/practice/");
  await page.getByRole("button", { name: "Full solve" }).click();
  await expect(page.getByTestId("scramble")).toHaveText(SCRAMBLE_RE, { timeout: 30_000 });
  const first = await page.getByTestId("scramble").textContent();
  await page.getByRole("button", { name: "Next scramble" }).click();
  await expect(page.getByTestId("scramble")).not.toHaveText(first!, { timeout: 30_000 });
});
