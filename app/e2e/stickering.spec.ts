/**
 * The three-tier stickering ladder, read off the SHIPPED page.
 *
 * The unit suite (tests/algs.spec.ts) renders the Astro components and reads
 * the same attribute; this reads it out of the built site in a real browser, on
 * the three routes that carry players — a case page, a lesson and the
 * reference. Both exist because of how the ladder shipped broken: every test
 * exercised `maskFor`/`stageMask` directly while the component called `maskFor`
 * with one argument fewer, so lib/ladders.ts had no renderer at all and 0 of
 * 185 cases showed a ladder mask. Anything asserted about tiering has to be
 * asserted about what reaches the page.
 *
 * Read the strings as: `-`/`O`/`P` full colour (what this step solves), `D`/`o`
 * dim (solved earlier, must be preserved), `I` grey (not yet reached).
 */
import { expect, test } from "@playwright/test";

import { ALL_CASES } from "../src/data/algs";
import { isLocked } from "../src/lib/unlocks";

const ATTR = "experimental-stickering-mask-orbits";

/** The mask attribute on the player inside `container`, or null if it has none. */
async function maskOn(page: import("@playwright/test").Page, container: string) {
  return page.locator(`${container} twisty-player`).first().getAttribute(ATTR);
}

test("a case page renders the ladder mask, not cubing.js's two tiers", async ({ page }) => {
  await page.goto("/case/oll.27/");
  // Sune: three corners misoriented (`O`), the fourth already oriented (`o`),
  // the yellow edges dim because OLL's edge half is done, the centres dim —
  // never grey. Before the ladder was wired in this attribute was cubing.js's
  // OLL scope, which lights the whole last layer.
  expect(await maskOn(page, "body")).toBe("EDGES:DDDDooooDDDD,CORNERS:DDDDOOOo,CENTERS:DDDDDD");
});

test("the two case pages one algorithm cannot identify still get their own stage", async ({
  page,
}) => {
  // eo.line and oll.45 are the SAME algorithm, `F R U R' U' F'`, at different
  // stages of different ladders, so `contextForPlayer` refuses to resolve them
  // from (puzzle, stickering, alg) — refusing beats coin-flipping. Until
  // /case/[...id] passed `context={contextForCase(def)}` these two pages were
  // the last two of 185 still shipping cubing.js's stock two tiers:
  // `CORNERS:DDDDOOOO`, all four last-layer corners lit, on a page about
  // orienting EDGES. Every other case page resolved through the fallback,
  // which is exactly why this survived review.
  await page.goto("/case/eo.line/");
  expect(await maskOn(page, "body")).toBe("EDGES:DDDDoOoODDDD,CORNERS:DDDDIIII,CENTERS:DDDDDD");
  await page.goto("/case/oll.45/");
  expect(await maskOn(page, "body")).toBe("EDGES:DDDDoOoODDDD,CORNERS:DDDDooOO,CENTERS:DDDDDD");
});

test("EVERY built case page carries a three-tier mask", async ({ page, baseURL }) => {
  // Read out of the shipped HTML rather than a rendered component: the whole
  // defect being gated here was a renderer that called a correct function with
  // one argument fewer, which no amount of unit testing could see. The page
  // list comes from the SITEMAP, so it is every case route this build actually
  // publishes — and not whatever a listing page happens to have rendered
  // eagerly. The expected count is DERIVED from the same unlock predicate the
  // build uses, so locking or unlocking a set moves this number on its own;
  // it was hardcoded to 138 and went stale the first time a case was locked.
  const expected = ALL_CASES.filter((c) => !isLocked(c)).length;
  const sitemap = await (await page.request.get(`${baseURL}/sitemap-0.xml`)).text();
  const urls = [...sitemap.matchAll(/<loc>([^<]*\/case\/[^<]*)<\/loc>/g)].map((m) => m[1]!);
  expect(urls.length, `sitemap case pages != unlocked cases`).toBe(expected);
  expect(expected).toBeLessThan(ALL_CASES.length);

  const bad: string[] = [];
  for (const url of urls) {
    const html = await (await page.request.get(url.replace(/^https?:\/\/[^/]+/, baseURL!))).text();
    const mask = new RegExp(`${ATTR}="([^"]*)"`).exec(html)?.[1];
    // A missing attribute is the two-tier fallback; a grey centre is
    // cubing.js's own F2L scope leaking through. Both shipped once.
    if (!mask) bad.push(`${url}: no mask`);
    else if (/CENTERS[0-9]*:[^,"]*I/.test(mask)) bad.push(`${url}: grey centre — ${mask}`);
  }
  expect(bad).toEqual([]);
});

test("an F2L case page no longer greys the yellow centre", async ({ page }) => {
  await page.goto("/case/f2l.1/");
  const mask = await maskOn(page, "body");
  // cubing.js's own F2L scope is `CENTERS:I-----`: a grey U centre on all 41
  // F2L cases. A centre is the frame every recognition cue is written against.
  expect(mask).toBe("EDGES:DDDDIIII-DDD,CORNERS:-DDDIIII,CENTERS:DDDDDD");
  expect(mask).not.toContain("CENTERS:I");
});

test("a 4x4 case page renders a mask at all", async ({ page }) => {
  await page.goto("/case/444.oll-parity/");
  const mask = await maskOn(page, "body");
  // Every 4x4/5x5 case used to render the attribute literally absent, because
  // `build()` returned undefined for anything but 3x3 — one tier, 63 cases.
  expect(mask).toBe(
    "CORNERS:DDDDIIII,EDGES:DDDDDDoDDDoDDDODDDoDoOoo,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
  );
});

test("the yellow-cross lesson stops claiming the last-layer corners", async ({ page }) => {
  await page.goto("/learn/yellow-cross/");
  const mask = await maskOn(page, "body");
  // The lesson's player declares stickering "OLL", whose scope covers the
  // corners, so it used to light all four of them three lessons before corner
  // orientation is taught. On the BEGINNER ladder this is the `eo` step: the
  // corners have not been reached, so they are grey.
  expect(mask).toBe("EDGES:DDDDoOoODDDD,CORNERS:DDDDIIII,CENTERS:DDDDDD");
});

test("a beginner-ladder lesson dims the cross and lights one corner", async ({ page }) => {
  await page.goto("/learn/white-corners/");
  expect(await maskOn(page, "body")).toBe("EDGES:DDDDIIIIIIII,CORNERS:-DDDIIII,CENTERS:DDDDDD");
});

test("every player on the reference carries a mask", async ({ page }) => {
  await page.goto("/reference/");
  const missing = await page.evaluate((attr) => {
    const out: string[] = [];
    for (const row of document.querySelectorAll("details[data-case]")) {
      const player = row.querySelector("twisty-player");
      if (!player?.getAttribute(attr)) out.push(row.getAttribute("data-case") ?? "?");
    }
    return out;
  }, ATTR);
  expect(missing).toEqual([]);
});
