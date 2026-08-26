import { expect, test } from "@playwright/test";

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
    const open = document.querySelector("details[open] twisty-player") as any;
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
// resolve, and each must name its own place in the ladder.
for (const [route, heading] of [
  ["/c0", "First solve"],
  ["/c1", "Two-look"],
  ["/c2", "One-look PLL"],
  ["/c3", "Annex"],
] as const) {
  test(`printed route ${route} resolves and names its card`, async ({ page }) => {
    const res = await page.goto(route);
    expect(res?.status(), `${route} must not 404 — it is printed on card stock`).toBe(200);
    await expect(page.locator("h1")).toContainText(heading);
    // Every card page offers its own reprint, so a lost card is one click away.
    await expect(page.locator('a[href^="/cards/"]').first()).toBeVisible();
  });
}

test("print page offers the whole set and every single card", async ({ page }) => {
  await page.goto("/print/");
  await expect(page.locator('a[href="/cards/deck-a4-fold.pdf"]')).toBeVisible();
  for (const n of [0, 1, 2, 3]) {
    await expect(page.locator(`a[href="/c${n}"]`)).toBeVisible();
  }
});
