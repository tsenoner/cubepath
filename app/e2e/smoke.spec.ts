import { expect, test } from "@playwright/test";

test("M0 proof: players render and scrambles generate on-device", async ({ page }) => {
  await page.goto("/");

  // On-device WCA scramble resolves to a real move sequence.
  const scramble = page.getByTestId("scramble");
  await expect(scramble).not.toHaveText("…", { timeout: 30_000 });
  await expect(scramble).not.toContainText("failed", { timeout: 30_000 });
  await expect(scramble).toHaveText(/^([RLUDFB][2']? ){10,}[RLUDFB][2']?$/, { timeout: 30_000 });

  // Both twisty-players actually render (closed shadow DOM — use the
  // player's own screenshot API as the rendering proof).
  await page.waitForFunction(() => document.querySelectorAll("twisty-player").length === 2);
  const shots = await page.evaluate(async () => {
    const players = [...document.querySelectorAll("twisty-player")] as any[];
    return Promise.all(players.map((p) => p.experimentalScreenshot({ width: 64, height: 64 })));
  });
  expect(shots).toHaveLength(2);
  for (const s of shots) expect(s).toMatch(/^data:image\/png;base64,/);
});
