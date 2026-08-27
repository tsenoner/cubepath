import { expect, test } from "@playwright/test";

// Node's ESM loader (which Playwright uses directly, unlike Vite) requires the
// import attribute for JSON.
import manifest from "../src/data/cards.json" with { type: "json" };

const SCRAMBLE_RE = /^([RLUDFB][2']? ){10,}[RLUDFB][2']?$/;

test("home shows the course ladder", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Speedcubing from zero");
  await expect(page.locator('a[href^="/learn/"]').first()).toBeVisible();
});

test("lesson page renders its case players", async ({ page }) => {
  await page.goto("/learn/two-look-oll/");
  await expect(page.locator("h1")).toContainText("Anti-Sune");
  await page.waitForFunction(() => document.querySelectorAll("twisty-player").length >= 7);
  // The lesson opens one case by default — its player must actually render.
  const shot = await page.evaluate(async () => {
    // twisty-player is a custom element; experimentalScreenshot is cubing.js API.
    const open = document.querySelector("details[open] twisty-player") as
      | (Element & {
          experimentalScreenshot(o: { width: number; height: number }): Promise<string>;
        })
      | null;
    return open?.experimentalScreenshot({ width: 48, height: 48 });
  });
  expect(shot).toMatch(/^data:image\/png;base64,/);
});

test("practice: drill scrambles + WCA full-solve scrambles on-device", async ({ page }) => {
  await page.goto("/practice/");
  await expect(page.getByTestId("scramble")).not.toHaveText("…", { timeout: 15_000 });
  await expect(page.getByTestId("scramble")).not.toContainText("thinking");
  await page.getByRole("button", { name: "Full solve" }).click();
  await expect(page.getByTestId("scramble")).toHaveText(SCRAMBLE_RE, { timeout: 30_000 });
});

// /c0../c3 are printed on physical cards. A printed card cannot be
// redeployed, so these paths are a permanent public contract — they must
// resolve, and each must name its own place in the ladder. Driven from the
// manifest so a fifth card extends the contract instead of slipping past it.
for (const card of manifest.cards) {
  test(`printed route ${card.route} resolves and names its card`, async ({ page }) => {
    const res = await page.goto(card.route);
    expect(res?.status(), `${card.route} must not 404 — it is printed on card stock`).toBe(200);
    await expect(page.locator("h1")).toContainText(card.title);
    // Every card page offers its own reprint, so a lost card is one click away.
    await expect(page.locator('a[href^="/cards/"]').first()).toBeVisible();
  });
}

// The cards also print bare site URLs in their prose, and those are the same
// contract as /c0../c3 — ink cannot be redeployed. /learn shipped as a 404
// because the course index lives at "/" and `learn/[...slug]` only emits
// lesson pages. Keep this list in step with the URLs cards.py prints.
for (const path of ["/learn", "/practice", "/print"]) {
  test(`URL printed on a card resolves: ${path}`, async ({ request }) => {
    const res = await request.get(path);
    expect(res.status(), `${path} is printed on a card and must not 404`).toBe(200);
  });
}

test("print page offers the whole set and every single card", async ({ page }) => {
  await page.goto("/print/");
  // The duplex sheets live inside a collapsed <details>, so the contract is
  // that every sheet is offered, not that every one is on screen unexpanded.
  for (const sheet of manifest.sheets) {
    await expect(page.locator(`a[href="/cards/${sheet.file}"]`)).toBeAttached();
  }
  for (const card of manifest.cards) {
    await expect(page.locator(`a[href="${card.route}"]`)).toBeVisible();
  }
});

// A visible link to a PDF the build never wrote still looks perfect on the
// page. Fetch every printable the manifest advertises and check it resolves.
test("every printable the print page offers actually resolves", async ({ page, request }) => {
  await page.goto("/print/");
  const hrefs = await page
    .locator('a[href^="/cards/"]')
    .evaluateAll((as) => as.map((a) => a.getAttribute("href")!));
  expect(hrefs.length).toBeGreaterThan(0);
  for (const href of new Set(hrefs)) {
    const res = await request.get(href);
    expect(res.status(), `${href} is linked from /print but does not resolve`).toBe(200);
  }
});
