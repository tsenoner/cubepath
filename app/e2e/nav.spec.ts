import { expect, test, type Page } from "@playwright/test";

import { PHASES, phaseAnchor } from "../src/data/phases";

/**
 * Navigation and wayfinding, gated.
 *
 * Every assertion here failed before the change that introduced it, and each
 * one is a defect a reader hit rather than a style preference. The measurements
 * in the comments are from a 390x844 phone against the real build.
 */

const PHONE = { width: 390, height: 844 };

/** Mark lessons complete the way LessonMeta does, then reload. */
async function seedLessons(page: Page, slugs: string[]): Promise<void> {
  await page.goto("/learn/notation/");
  // The lesson page opens the database and creates the stores.
  await page.waitForFunction(() => "indexedDB" in window);
  await page.waitForTimeout(400);
  await page.evaluate(async (list) => {
    const db = await new Promise<IDBDatabase>((res, rej) => {
      const r = indexedDB.open("cubepath");
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error);
    });
    if (!db.objectStoreNames.contains("lessons")) throw new Error("no lessons store");
    await new Promise<void>((res, rej) => {
      const tx = db.transaction("lessons", "readwrite");
      const store = tx.objectStore("lessons");
      for (const slug of list) store.put({ slug, completedAt: new Date() });
      tx.oncomplete = () => res();
      tx.onerror = () => rej(tx.error);
    });
    db.close();
  }, slugs);
}

/** The bottom of the sticky chrome: the header, plus any second sticky bar. */
async function chromeBottom(page: Page): Promise<number> {
  return page.evaluate(() => {
    const rect = (s: string) => document.querySelector(s)?.getBoundingClientRect().bottom ?? 0;
    return Math.max(rect(".site-header"), rect(".toolbar"));
  });
}

// ── The course index has addresses ───────────────────────────────────
// Driven from PHASES, so a ninth phase is covered the day it ships.
test("every phase is addressable, and its jump chip resolves", async ({ page }) => {
  await page.goto("/");
  for (const phase of PHASES) {
    const id = phaseAnchor(phase.key);
    const card = page.locator(`[id="${id}"]`);
    // A phase with no lessons is not rendered; the jump bar must agree.
    const chip = page.locator(`[data-phase-jump="${phase.key}"]`);
    expect(await card.count(), `#${id} and its chip must both exist or neither`).toBe(
      await chip.count(),
    );
    if ((await card.count()) === 0) continue;
    await expect(chip).toHaveAttribute("href", `#${id}`);
  }
});

test("a phase anchor lands clear of the sticky header", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await page.goto(`/#${phaseAnchor("444")}`);
  await page.waitForTimeout(600);
  const top = await page
    .locator(`[id="${phaseAnchor("444")}"]`)
    .evaluate((el) => el.getBoundingClientRect().top);
  expect(top, "the 4x4 phase card must not sit under the header").toBeGreaterThanOrEqual(
    await chromeBottom(page),
  );
});

// ── The breadcrumb tells the truth ───────────────────────────────────
test("no lesson calls the course a 3x3 course, and the phase crumb goes somewhere", async ({
  page,
}) => {
  // 444-centers is one of the six lessons whose crumb read "3×3 course › 4×4".
  await page.goto("/learn/444-centers/");
  const crumbs = page.locator(".crumbs");
  await expect(crumbs).not.toContainText("3×3 course");
  await expect(crumbs.locator("a").first()).toHaveText("Learn");
  await expect(crumbs.locator("a").nth(1)).toHaveAttribute("href", `/#${phaseAnchor("444")}`);
});

test("the active header link is announced, not just coloured", async ({ page }) => {
  await page.goto("/reference/");
  // Exactly the page: /reference/ is both the section and the URL.
  await expect(page.locator('.navlink[aria-current="page"]')).toHaveText("Reference");
  // A lesson is inside "Learn" without being it.
  await page.goto("/learn/notation/");
  await expect(page.locator('.navlink[aria-current="true"]')).toHaveText("Learn");
});

// ── Progress is written by more than one click target ────────────────
test("reaching the end of a lesson records it, without touching the pager", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await page.goto("/learn/white-cross/");
  // A real reader scrolls; the observer is deliberately gated on that.
  await page.mouse.wheel(0, 500);
  await page.locator("[data-lesson-end]").scrollIntoViewIfNeeded();
  await expect(page.locator("[data-lesson-done]")).toBeVisible({ timeout: 8000 });

  // …and the course index picks it up.
  await page.goto("/");
  await expect(page.locator('[data-lesson-slug="white-cross"][data-complete]')).toHaveCount(1);
});

test("the course index marks the phase you are in, and resumes into it", async ({ page }) => {
  await seedLessons(page, [
    "cube-anatomy",
    "notation",
    "white-cross",
    "white-corners",
    "second-layer",
    "yellow-cross",
    "align-edges",
    "position-corners",
    "orient-corners",
    "speed-tricks",
    "cross-planning",
    "finger-tricks",
  ]);
  await page.goto("/");
  await expect(page.locator("[data-hero-cta]")).toHaveText("Resume lesson");
  await expect(page.locator("[data-resume-title]")).not.toBeEmpty();
  // The marker is on the phase holding the lesson you would resume — the whole
  // point being that it survives the hero scrolling off a 5,100px page.
  const current = page.locator('[data-phase][data-state="current"]');
  await expect(current).toHaveCount(1);
  await expect(current.locator("[data-here]")).toBeVisible();
  await expect(page.locator(".phase-jump .chip.here")).toHaveCount(1);
});

// ── Anchors land where they are aimed ────────────────────────────────
// The round trip the site advertises: a case page's "See it in the reference".
// 107 of the 120 tiles own such an anchor, and `.tile` was the one anchored
// element on the page with no clearance — measured ZERO visible pixels behind
// 154px of sticky chrome, in Chromium and WebKit alike.
for (const [caseId, kind] of [
  ["oll.40", "a tile"],
  ["f2l.12", "a tile"],
  ["oll.27", "a row"],
] as const) {
  test(`the reference anchor for ${caseId} (${kind}) clears the sticky bars`, async ({ page }) => {
    await page.setViewportSize(PHONE);
    await page.goto(`/case/${caseId}/`);
    const href = await page.locator('a[href^="/reference/#"]').first().getAttribute("href");
    expect(href, "the case page must offer its place in the reference").toBeTruthy();
    await page.goto(href!);
    await page.waitForTimeout(800);
    const id = href!.split("#")[1]!;
    const box = await page.locator(`[id="${id}"]`).evaluate((el) => el.getBoundingClientRect().top);
    expect(box, `${id} must not be hidden behind the toolbar`).toBeGreaterThanOrEqual(
      await chromeBottom(page),
    );
  });
}

// ── The filter ───────────────────────────────────────────────────────
test("the filter matches what a cuber types, and says what it found", async ({ page }) => {
  await page.goto("/reference/");
  const search = page.locator("[data-ref-search]");
  const shown = () => page.locator("[data-search]:not([hidden])");

  // Every one of these returned zero before lib/search.ts.
  for (const q of ["t perm", "u perm", "4x4", "awkward", "anti sune", "parity"]) {
    await search.fill(q);
    expect(await shown().count(), `"${q}" must find something`).toBeGreaterThan(0);
  }
  // …and "t perm" must find the T-Perm, not all 25 perms.
  await search.fill("t perm");
  expect(await shown().count()).toBeLessThanOrEqual(2);

  await search.fill("zzzzqqq");
  await expect(page.locator("[data-ref-count]")).toContainText("try a case name");
});

test("filtering keeps the reader with the results, and clearing puts them back", async ({
  page,
}) => {
  await page.setViewportSize(PHONE);
  await page.goto("/reference/");
  await page.waitForTimeout(400);
  const search = page.locator("[data-ref-search]");
  await search.focus();
  await page.evaluate(() => window.scrollTo(0, 6000));
  await page.waitForTimeout(200);
  const before = await page.evaluate(() => window.scrollY);
  expect(before, "the test needs a page tall enough to scroll into").toBeGreaterThan(3000);

  await page.keyboard.type("ua");
  await page.waitForTimeout(400);
  const firstTop = await page
    .locator("[data-search]:not([hidden])")
    .first()
    .evaluate((el) => el.getBoundingClientRect().top);
  expect(firstTop, "the top match must be below the toolbar, not above the fold").toBeGreaterThan(
    await chromeBottom(page),
  );

  // Escape clears — Firefox renders no cancel button, so this is the only exit.
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
  expect(Math.abs((await page.evaluate(() => window.scrollY)) - before)).toBeLessThan(40);
});

test("a jump chip the filter emptied is inert, not a dead link", async ({ page }) => {
  await page.goto("/reference/");
  await page.locator("[data-ref-search]").fill("ua");
  await page.waitForTimeout(300);
  const off = page.locator(".jump .chip.off");
  expect(await off.count()).toBeGreaterThan(0);
  for (const chip of await off.all()) {
    await expect(chip).toHaveAttribute("aria-disabled", "true");
    expect(await chip.evaluate((el) => (el as HTMLElement).tabIndex)).toBe(-1);
  }
});

test("a jump chip moves focus to its section, not just the viewport", async ({ page }) => {
  await page.goto("/reference/");
  await page.locator('.jump .chip[data-jump="full-pll"]').click();
  await page.waitForTimeout(500);
  expect(await page.evaluate(() => document.activeElement?.id)).toBe("full-pll");
  await expect(page.locator('.jump .chip[aria-current="location"]')).toHaveCount(1);
});

// ── The filter input must not zoom iOS Safari ────────────────────────
test("no text input is under Safari's 16px zoom floor", async ({ page }) => {
  for (const path of ["/reference/", "/practice/", "/"]) {
    await page.goto(path);
    const sizes = await page.evaluate(() =>
      [...document.querySelectorAll("input")]
        .filter((i) => !["checkbox", "radio", "range", "file"].includes(i.type))
        .map((i) => ({ type: i.type, px: parseFloat(getComputedStyle(i).fontSize) })),
    );
    for (const s of sizes) {
      expect(
        s.px,
        `${path}: a ${s.type} input at ${s.px}px force-zooms iOS Safari`,
      ).toBeGreaterThanOrEqual(16);
    }
  }
});

// ── The skip link actually skips ─────────────────────────────────────
test("the skip link moves focus into the page", async ({ page }) => {
  await page.goto("/reference/");
  await page.keyboard.press("Tab");
  await expect(page.locator(".skip-link")).toBeFocused();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(200);
  expect(await page.evaluate(() => document.activeElement?.id)).toBe("main");
});

// ── Nothing moves after paint ────────────────────────────────────────
test("the course index does not reflow once progress loads", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await seedLessons(page, ["cube-anatomy", "notation", "white-cross", "white-corners"]);
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const cls = await page.evaluate(
    () =>
      new Promise<number>((resolve) => {
        let total = 0;
        new PerformanceObserver((list) => {
          for (const e of list.getEntries()) {
            const shift = e as PerformanceEntry & { value: number; hadRecentInput: boolean };
            if (!shift.hadRecentInput) total += shift.value;
          }
        }).observe({ type: "layout-shift", buffered: true });
        setTimeout(() => resolve(total), 2500);
      }),
  );
  // It was 0.107 — past the "good" threshold — on the site's front door, as the
  // Resume swap grew the primary button and dropped "All algorithms" 72px.
  expect(cls, "the hero must not move under a thumb that is already reaching").toBeLessThan(0.02);
});

// ── The two surfaces link to each other ──────────────────────────────
test("a lesson reaches its own cases and its reference section", async ({ page }) => {
  await page.goto("/learn/full-pll/");
  // `algorithms` is build-validated and was rendered nowhere: 37 ids, 8 lessons.
  const cases = page.locator('.taught a[href^="/case/"]');
  expect(await cases.count()).toBeGreaterThan(10);
  await expect(page.locator('.practice a[href^="/reference/#"]').first()).toBeVisible();
});

test("a case page reaches the reference row it came from and the lesson that teaches it", async ({
  page,
}) => {
  await page.goto("/case/pll.t/");
  await expect(page.locator(".crumbs a").first()).toHaveAttribute("href", "/reference/#pll-t");
  await expect(page.locator('.crumbs a[href^="/learn/"]')).toHaveCount(1);
});

test("a lesson can reach its phase siblings", async ({ page }) => {
  await page.goto("/learn/444-centers/");
  const nav = page.locator(".phase-nav");
  await expect(nav).toBeVisible();
  expect(await nav.locator("a").count()).toBeGreaterThan(1);
  await expect(nav.locator('a[aria-current="page"]')).toHaveCount(1);
});

// ── The phone pager is a target, not a ragged column ─────────────────
test("the pager is full width on a phone, and names a phase it crosses", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await page.goto("/learn/notation/");
  const next = page.locator(".pager-link.next");
  const main = page.locator("main");
  const nextW = (await next.boundingBox())!.width;
  const mainW = (await main.boundingBox())!.width;
  // It was capped at 46%, wrapping a lesson title to four lines.
  expect(nextW).toBeGreaterThan(mainW * 0.8);
  // notation is the last lesson of Basics, so Next leaves the phase.
  await expect(next.locator(".dir")).toContainText("Next phase");
});

// ── The whole ladder row is the tap target ───────────────────────────
test("tapping a lesson's description opens the lesson", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await page.goto("/");
  const desc = page.locator("[data-lesson-slug] .desc").first();
  const box = (await desc.boundingBox())!;
  // Click the DESCRIPTION's coordinates, not the link's. Playwright refuses a
  // normal .click() here precisely because the row overlay covers it, which is
  // the fix working: the whole 63.5px row is the target, not the 23px title.
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await expect(page).toHaveURL(/\/learn\//);
});

// ── The spy must not fight the reader ────────────────────────────────
// chip.scrollIntoView() walked every ancestor scroller and moved the DOCUMENT,
// because the chip sits inside the sticky toolbar, above the optimal viewing
// region html's scroll-padding establishes. The page jerked back 52px at every
// section boundary, in Chromium and WebKit alike, and never converged.
for (const vp of [
  { width: 1280, height: 900, name: "desktop" },
  { width: 390, height: 844, name: "phone" },
]) {
  test(`scrolling down /reference never moves the page backwards (${vp.name})`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto("/reference/");
    await page.waitForTimeout(600);
    const backward = await page.evaluate(async () => {
      const jumps: number[][] = [];
      for (let i = 0; i < 300; i++) {
        const before = window.scrollY;
        window.scrollBy(0, 25);
        await new Promise((r) => setTimeout(r, 8));
        const after = window.scrollY;
        if (after < before) jumps.push([before, after]);
      }
      return jumps;
    });
    expect(
      backward.slice(0, 5),
      "something is scrolling the document up while the reader scrolls down",
    ).toEqual([]);
  });
}

// ── The set's own size must not leak into its members' haystacks ─────
// The trainer names the sets "Full OLL (57)", "F2L (41)", "Full PLL (all 21)".
// Feeding those names to the filter verbatim put the count in all 57 members'
// haystacks, so searching "57" matched the whole set instead of OLL 57.
test("a number query finds the case with that number, not its whole set", async ({ page }) => {
  await page.goto("/reference/");
  const search = page.locator("[data-ref-search]");
  const shown = () => page.locator("[data-search]:not([hidden])");
  for (const [q, ceiling] of [
    ["57", 4],
    ["41", 4],
    ["21", 6],
  ] as const) {
    await search.fill(q);
    const n = await shown().count();
    expect(n, `"${q}" must not return a whole set`).toBeLessThanOrEqual(ceiling);
    expect(n, `"${q}" must still find its own case`).toBeGreaterThan(0);
  }
});

// ── A chip cannot be both "you are here" and "you cannot go here" ────
test("an empty filter result leaves no chip marked as the current location", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await page.goto("/reference/");
  await page.waitForTimeout(400);
  await page.evaluate(() => window.scrollTo(0, 5000));
  await page.waitForTimeout(400);
  await page.locator("[data-ref-search]").fill("zzzzqqq");
  await page.waitForTimeout(500);
  const bad = await page.evaluate(
    () => document.querySelectorAll('.jump .chip[aria-current][aria-disabled="true"]').length,
  );
  expect(bad, "a disabled chip must not also be aria-current").toBe(0);
});

// ── Every case page should be able to name the lesson that teaches it ─
test("the case-to-lesson back-link covers the full sets, not just the curated cases", async ({
  page,
  request,
}) => {
  await page.goto("/reference/");
  const ids = await page.evaluate(() => [
    ...new Set(
      [...document.querySelectorAll("[data-case]")].map((e) => (e as HTMLElement).dataset.case!),
    ),
  ]);
  let withLesson = 0;
  for (const id of ids) {
    const html = await (await request.get(`/case/${id}/`)).text();
    if (/<a[^>]+href="\/learn\//.test(html)) withLesson += 1;
  }
  // It was 33 of 125 while the fallback was keyed on CaseDef.group instead of
  // the trainer group — the whole of Full OLL, F2L and Full PLL fell through.
  expect(withLesson, `${withLesson}/${ids.length} case pages name their lesson`).toBeGreaterThan(
    ids.length * 0.9,
  );
});
