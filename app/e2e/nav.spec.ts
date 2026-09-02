import { expect, test, type Page } from "@playwright/test";

import { PHASES, phaseAnchor } from "../src/data/phases";
import { publishedRoutes } from "./routes";
import { SECTION_NAV, SECTIONS } from "../src/data/refsections";
import { isLocked } from "../src/lib/unlocks";

/**
 * Navigation and wayfinding, gated.
 *
 * Every assertion here failed before the change that introduced it, and each
 * one is a defect a reader hit rather than a style preference. The measurements
 * in the comments are from a 390x844 phone against the real build.
 */

/*
 * This file runs its tests in PARALLEL, and it is the only one that says so.
 *
 * It is the suite's critical path: 47 of the 165 tests, and the whole run used
 * to cost what this file alone costs, because Playwright parallelises across
 * FILES and serialises within one. Measured, both ways, three to four runs
 * each: at two workers (a 4-core CI runner's default) 35.1s -> 24.7s, and at
 * the seven a 14-core laptop uses, 35.7s -> 11.2s.
 *
 * Safe by construction rather than by luck: there is no beforeAll, no
 * afterAll and no module-level state here, and every test takes its own `page`
 * — so Playwright already gives each one an isolated context, which is what
 * IndexedDB seeding, viewport size and scroll position all live in. The tests
 * that measure scroll and layout are the ones to watch under CPU contention,
 * and they were clean across eight consecutive runs at both worker counts;
 * `retries: 1` in the config remains the backstop.
 */
test.describe.configure({ mode: "parallel" });

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

/**
 * The bottom of the sticky chrome.
 *
 * `.site-header` and nothing else: there is ONE sticky box per route, and a
 * page that needs its own bar renders it into Header's `pagenav` slot, as a row
 * INSIDE that box. This used to take `Math.max` with `.toolbar`, which is now a
 * descendant of the header and so can never contribute — a helper documenting a
 * two-box model the site no longer has.
 */
async function chromeBottom(page: Page): Promise<number> {
  return page.evaluate(
    () => document.querySelector(".site-header")?.getBoundingClientRect().bottom ?? 0,
  );
}

/**
 * Land on `#id` within `url` and return how far the target sits below the
 * sticky chrome. Negative means it is hidden behind it.
 *
 * Written once because four tests measured this, each with its own arbitrary
 * settle wait (200/400/600/800ms). It polls the real condition instead: the
 * anchor's position has to stop moving before it can be judged.
 */
async function clearanceOf(page: Page, url: string, id: string): Promise<number> {
  await page.goto(url);
  await page.waitForFunction((target) => !!document.getElementById(target), id);
  let last = Number.NaN;
  for (let i = 0; i < 25; i++) {
    const top = await page.locator(`[id="${id}"]`).evaluate((el) => el.getBoundingClientRect().top);
    if (Math.abs(top - last) < 1) break;
    last = top;
    await page.waitForTimeout(60);
  }
  return last - (await chromeBottom(page));
}

// ── The course index has addresses ───────────────────────────────────
// Driven from PHASES, so a ninth phase is covered the day it ships.
test("every phase is addressable, and its jump chip resolves", async ({ page }) => {
  await page.goto("/");
  for (const phase of PHASES) {
    const id = phaseAnchor(phase.key);
    const card = page.locator(`[id="${id}"]`);
    // A phase with no lessons is not rendered; the jump bar must agree.
    const chip = page.locator(`.pagenav a[href="#${id}"]`);
    expect(await card.count(), `#${id} and its chip must both exist or neither`).toBe(
      await chip.count(),
    );
    if ((await card.count()) === 0) continue;
    await expect(chip).toHaveAttribute("href", `#${id}`);
  }
});

test("a phase anchor lands clear of the sticky header", async ({ page }) => {
  await page.setViewportSize(PHONE);
  const id = phaseAnchor("444");
  const clear = await clearanceOf(page, `/#${id}`, id);
  expect(clear, "the 4x4 phase card must not sit under the header").toBeGreaterThanOrEqual(0);
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
  // `.resume`, not `.here`. The bar moved into the header's second row (so it
  // survives the hero scrolling off a 5,208px page instead of being stranded at
  // y=359), and it now answers TWO questions with two marks: `.here` is the
  // phase you have scrolled to, owned by the shared scroll-spy, and `.resume`
  // is the phase your progress is in. This assertion is about progress.
  await expect(page.locator(".pagenav .chip.resume")).toHaveCount(1);
});

// ── Anchors land where they are aimed ────────────────────────────────
// The round trip the site advertises: a case page's "See it in the reference".
// 106 of the 119 tiles own such an anchor, and `.tile` was the one anchored
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
    const id = href!.split("#")[1]!;
    const clear = await clearanceOf(page, href!, id);
    expect(clear, `${id} must not be hidden behind the toolbar`).toBeGreaterThanOrEqual(0);
  });
}

// ── The filter ───────────────────────────────────────────────────────
test("the filter matches what a cuber types, and says what it found", async ({ page }) => {
  await page.goto("/reference/");
  const search = page.locator("[data-ref-search]");
  const shown = () => page.locator("[data-search]:not([hidden])");

  // `expect.poll`, not a bare `count()`: the filter applies once per animation
  // frame rather than synchronously inside the input handler, so reading the
  // DOM the instant `fill()` resolves races it. These used to pass only because
  // the handler happened to be synchronous — a contract no test asked for.
  const count = () => expect.poll(() => shown().count());

  // Every one of these returned zero before lib/search.ts.
  for (const q of ["t perm", "u perm", "4x4", "awkward", "anti sune", "parity"]) {
    await search.fill(q);
    await count().toBeGreaterThan(0);
  }
  // …and "t perm" must find the T-Perm, not all 25 perms.
  await search.fill("t perm");
  await count().toBeLessThanOrEqual(2);

  await search.fill("zzzzqqq");
  // Asserted on the whole `role="status"` region, not on the visible span: the
  // announcement is what this gate is about, and the guidance sentence now
  // lives in an `.sr-only` sibling inside that same region. It had to move —
  // the visible span is `white-space: nowrap` inside a grid, so putting a
  // 93-character sentence in it made /reference 872px wide on a 375px phone.
  // Both halves are still announced together, and the visible count stays
  // bounded.
  await expect(page.locator("[data-ref-status]")).toContainText(/try a case name/i);
  // Pattern, not a literal: the entry count moves whenever a set is taught or
  // locked, and a hardcoded total here would go stale silently.
  await expect(page.locator("[data-ref-count]")).toHaveText(/^0 of \d+ shown$/);
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
  await expect(page.locator("[data-ref-count]")).toHaveText(/^\d+ of \d+ shown$/);
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

// The same defect one page over. /reference's fix lived in /reference's script,
// so /glossary — which hides whole groups on a query — shipped live chips over
// `display: none` sections. `markEmptySections` is shared now, and this is the
// gate that says so.
test("a glossary chip the filter emptied is inert too", async ({ page }) => {
  await page.goto("/glossary/");
  await page.locator("[data-gloss-search]").fill("dedge");
  await page.waitForTimeout(300);
  const off = page.locator(".pagenav .chip.off");
  expect(await off.count(), "a narrow query must empty at least one group").toBeGreaterThan(0);
  for (const chip of await off.all()) {
    await expect(chip).toHaveAttribute("aria-disabled", "true");
    expect(await chip.evaluate((el) => (el as HTMLElement).tabIndex)).toBe(-1);
  }
  // …and a chip that still has matches stays a live link.
  const live = page.locator(".pagenav .chip:not(.off)");
  expect(await live.count()).toBeGreaterThan(0);
  await expect(live.first()).toHaveAttribute("aria-disabled", "false");
});

test("a jump chip moves focus to its section, not just the viewport", async ({ page }) => {
  await page.goto("/reference/");
  await page.locator('.jump .chip[data-jump="full-pll"]').click();
  await page.waitForTimeout(500);
  expect(await page.evaluate(() => document.activeElement?.id)).toBe("full-pll");
  await expect(page.locator('.jump .chip[aria-current="location"]')).toHaveCount(1);
});

// ── The filter input must not zoom iOS Safari ────────────────────────
// Every app surface, from the sitemap — not a hand-typed three. The list said
// /reference, /practice and /, and the page it omitted (/glossary) was the one
// that shipped a 15px filter: the fix had been pasted into /reference rather
// than shared, and the gate that should have noticed could not see the page.
// `/case/` is excluded because it is 134 pages of one template with no input.
const INPUT_ROUTES = publishedRoutes().filter((r) => !r.startsWith("/case/"));

test("no text input is under Safari's 16px zoom floor", async ({ page }) => {
  for (const path of INPUT_ROUTES) {
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
    // Polled: the filter lands on the next frame, not inside the handler.
    await expect
      .poll(() => shown().count(), { message: `"${q}" must not return a whole set` })
      .toBeLessThanOrEqual(ceiling);
    expect(await shown().count(), `"${q}" must still find its own case`).toBeGreaterThan(0);
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
  // It was 33 of the then-125 while the fallback was keyed on CaseDef.group
  // and not the trainer group — Full OLL, F2L and Full PLL all fell through.
  expect(withLesson, `${withLesson}/${ids.length} case pages name their lesson`).toBeGreaterThan(
    ids.length * 0.9,
  );
});

// ── The glossary is an anchor destination too ────────────────────────
// The lessons auto-link the first mention of every term, so `/glossary/#<term>`
// is the site's commonest anchor jump by a wide margin. It was also the one
// anchored page still writing its own `scroll-margin`: tokens.css already
// insets the scrollport with `html { scroll-padding-block-start }`, and
// scroll-margin EXPANDS the target, so the two stacked and every definition
// landed ~65px lower than aimed — the exact failure CLAUDE.md names and
// /reference was already fixed for. Driven from the page's own entries so a
// new term is covered the day it ships.
test("a glossary term lands clear of the sticky header, not a header lower", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await page.goto("/glossary/");
  const ids = (await page.locator(".entry[id]").evaluateAll((els) => els.map((e) => e.id))).slice(
    0,
    5,
  );
  expect(ids.length, "the glossary must render addressable entries").toBeGreaterThan(0);
  for (const id of ids) {
    const clear = await clearanceOf(page, `/glossary/#${id}`, id);
    expect(clear, `#${id} must not sit under the header`).toBeGreaterThanOrEqual(0);
    // …and not a whole header BELOW it either, which is what stacking looked
    // like: clearance is one --space-3 gap, so allow a small tolerance only.
    expect(
      clear,
      `#${id} landed ${Math.round(clear)}px below the chrome — anchors stacked`,
    ).toBeLessThan(48);
  }
});

// ── Every lesson can be navigated from inside itself ─────────────────
// Driven from the sitemap, so lesson 26 is covered the day it ships.
//
// The defect: 25 of 25 lessons carry >= 4 headings, 180 in all, and every one
// already had an `id` — yet nothing pointed at any of them. Measured on the
// longest lesson (9,743px, 11.5 phone screens): at y=4,800 the only links on
// screen were the five header destinations, because the breadcrumb sits at
// y=73 and the next navigation is the pager at y=9,402.
test("every lesson carries an outline whose every chip resolves and lands clear", async ({
  page,
}) => {
  await page.setViewportSize(PHONE);
  // From the SITEMAP: `astro:content` is a build-time module and cannot be
  // imported here, and a hand-written list of 25 slugs is exactly the staleness
  // this suite exists to catch. Through the shared reader, which walks every
  // shard — this fetched `sitemap-0.xml` by name, so the sweep would have
  // stopped being exhaustive at the shard boundary without saying so.
  const slugs = publishedRoutes()
    .filter((r) => r.startsWith("/learn/"))
    .map((r) => r.split("/").filter(Boolean)[1]!);
  expect(slugs.length, "the sitemap must list the lessons").toBeGreaterThan(20);

  for (const slug of slugs) {
    await page.goto(`/learn/${slug}/`);
    const chips = page.locator(".pagenav .chip");
    const n = await chips.count();
    // Universal, not conditional: the layout's own "What you'll learn" and
    // "Practice" headings bracket the body's, so no lesson can fall below three.
    expect(n, `${slug} must carry an outline`).toBeGreaterThanOrEqual(3);

    const ids = await chips.evaluateAll((els) =>
      els.map((e) => (e as HTMLAnchorElement).getAttribute("href")!.slice(1)),
    );
    // getElementById, never querySelector("#"+id): six shipped heading ids
    // begin with a digit, which are legal fragments and illegal selectors.
    const missing = await page.evaluate(
      (list) => list.filter((id) => !document.getElementById(id)),
      ids,
    );
    expect(missing, `${slug}: chips point at ids that do not exist`).toEqual([]);
  }
});

test("a lesson outline chip lands its heading clear of the two-row header", async ({ page }) => {
  await page.setViewportSize(PHONE);
  // The longest lesson, and the one with the most chips.
  await page.goto("/learn/full-oll-overview/");
  const ids = await page
    .locator(".pagenav .chip")
    .evaluateAll((els) => els.map((e) => (e as HTMLAnchorElement).getAttribute("href")!.slice(1)));
  expect(ids.length).toBeGreaterThan(3);
  for (const id of ids) {
    const clear = await clearanceOf(page, `/learn/full-oll-overview/#${id}`, id);
    expect(clear, `#${id} landed under the sticky header`).toBeGreaterThanOrEqual(0);
  }
});

// The documented exception, now that "does this finish the lesson" is declared
// in frontmatter rather than guessed from the href. white-cross.mdx offers the
// printable cards; crediting the lesson because the reader went to fetch them
// would hide it from Resume permanently.
test("a practice link that is not an exit is not tagged as one", async ({ page }) => {
  await page.goto("/learn/white-cross/");
  await expect(page.locator('a.btn[href="/practice/"]')).toHaveAttribute("data-lesson-advance", "");
  expect(await page.locator('a.btn[href="/print"][data-lesson-advance]').count()).toBe(0);
  await expect(page.locator('a.btn[href="/print"]')).toBeVisible();
});

// The bar must NOT be a completion writer. Crediting a lesson for jumping to
// its own Practice heading would mark it done and hide it from Resume forever —
// the same trap `white-cross.mdx` pointing at /print already documents.
test("no outline chip is tagged as a lesson-completion exit", async ({ page }) => {
  await page.goto("/learn/two-look-oll/");
  expect(await page.locator(".pagenav .chip[data-lesson-advance]").count()).toBe(0);
});

// ── The trainer is not a sink ────────────────────────────────────────
// Every other surface points INTO /practice — all 25 lessons and all 134 case
// pages — and /practice pointed nowhere: `main` held ZERO <a> elements. A
// reader who drilled a case, failed it and wanted to study it had no route out
// except the browser's back button.
test("the trainer links back out to the reference and to the case it is drilling", async ({
  page,
}) => {
  await page.goto("/practice/");

  // Every set names its reference section. A trainer group key IS a section id,
  // so a dead fragment here means the two lists have drifted apart.
  const frags = await page
    .locator('main a[href^="/reference/#"]')
    .evaluateAll((els) => els.map((e) => (e as HTMLAnchorElement).getAttribute("href")!));
  expect(frags.length, "each drillable set must name its reference section").toBeGreaterThan(0);
  await page.goto("/reference/");
  const dead = await page.evaluate(
    (list) => list.filter((h) => !document.getElementById(h.split("#")[1]!)),
    frags,
  );
  expect(dead, "trainer -> reference fragments that resolve to nothing").toEqual([]);

  // …and the case being drilled can be opened.
  await page.goto("/practice/");
  await page.getByRole("button", { name: "Show case" }).click();
  const href = await page.locator("#case-link").getAttribute("href");
  expect(href, "the drilled case must be reachable").toMatch(/^\/case\/.+\/$/);
  const res = await page.goto(href!);
  expect(res?.status(), `${href} must be a real page`).toBe(200);
});

// ── The jump bar is reachable from anywhere on the page ──────────────
// The course index's bar was `position: static` at y=359 on a 5,208px page, so
// the only way to reach a phase was to already be in the first of 6.2 screens —
// the one screen where the phases are visible anyway. It is a row inside the
// sticky header now.
for (const route of ["/", "/glossary/", "/learn/full-oll-overview/"] as const) {
  test(`${route}: the jump bar is still on screen after scrolling deep`, async ({ page }) => {
    await page.setViewportSize(PHONE);
    await page.goto(route);
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    expect(height, `${route} must be long enough for this to matter`).toBeGreaterThan(844 * 3);
    await page.evaluate(() => window.scrollTo(0, Math.round(document.body.scrollHeight * 0.6)));
    await page.waitForTimeout(300);
    const box = await page.locator(".site-header .pagenav").boundingBox();
    expect(box, `${route}: the bar must exist in the header`).not.toBeNull();
    expect(box!.y, `${route}: the bar scrolled off screen`).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height, `${route}: the bar is below the fold`).toBeLessThanOrEqual(844);
  });
}

// …and the short surfaces deliberately have none. A jump bar on a 1.1-screen
// page is chrome with nothing to navigate; /practice is 951px and /print is
// 2,088px at 390x844. If either grows past a few screens, revisit — but do not
// add a bar because the other pages have one.
for (const route of ["/practice/", "/print/"] as const) {
  test(`${route}: no jump bar, because the page is too short to need one`, async ({ page }) => {
    await page.setViewportSize(PHONE);
    await page.goto(route);
    expect(await page.locator(".site-header .pagenav").count()).toBe(0);
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    expect(height, `${route} has grown — reconsider whether it needs a bar`).toBeLessThan(844 * 4);
  });
}

// ── Wide screens: the outline moves into the margin ──────────────────
// A lesson's text line is 612px because --measure-prose caps it at ~72
// characters, which leaves 390px empty on each side at 1440px and 630px at
// 1920px. The outline is what fills it. `position: fixed` takes the bar out of
// the header's flow, so the header returns to one thin row and the sidebar
// costs no vertical chrome at all — measured 167px -> 55px at the breakpoint.
for (const route of ["/", "/glossary/", "/learn/full-oll-overview/"] as const) {
  test(`${route}: the outline becomes a margin sidebar at >=1100px`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(route);
    await page.waitForTimeout(300);

    const r = await page.evaluate(() => {
      const bar = document.querySelector(".pagenav")!;
      const p = document.querySelector("main p")!;
      const bb = bar.getBoundingClientRect();
      const pb = p.getBoundingClientRect();
      const chips = [...bar.querySelectorAll(".chip")];
      return {
        position: getComputedStyle(bar).position,
        gapToText: Math.round(pb.left - bb.right),
        onScreen: bb.left >= 0 && bb.top >= 0,
        // the whole point of a column: every chip legible at once, no scrolling
        allChipsInView: chips.every((c) => {
          const r = c.getBoundingClientRect();
          return r.top >= bb.top - 1 && r.bottom <= bb.bottom + 1;
        }),
        chips: chips.length,
        headerH: Math.round(document.querySelector(".site-header")!.getBoundingClientRect().height),
        hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      };
    });

    expect(r.position, "the bar must leave the header flow at desktop").toBe("fixed");
    expect(r.onScreen, "the sidebar must be on screen").toBe(true);
    // It must not collide with the prose it sits beside.
    expect(r.gapToText, "the sidebar overlaps the text column").toBeGreaterThan(0);
    expect(r.allChipsInView, "every chip must be readable without scrolling").toBe(true);
    expect(r.chips).toBeGreaterThan(2);
    // Out of flow means the header is one row again — the sidebar is free.
    expect(r.headerH, "the header must shed the bar's height at desktop").toBeLessThan(90);
    expect(r.hscroll).toBe(false);
  });
}

test("below the breakpoint the outline is still the in-header strip", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto("/learn/full-oll-overview/");
  const pos = await page.evaluate(
    () => getComputedStyle(document.querySelector(".pagenav")!).position,
  );
  expect(pos, "1024px is below the sidebar breakpoint").not.toBe("fixed");
  expect(await page.locator(".site-header .pagenav").count()).toBe(1);
});

// ── The outline knows where you are ──────────────────────────────────
// Same machinery as /reference's strip, from lib/jumpbar.ts. The bar was
// write-only before: 16 chips and nothing saying which section you were in.
test("the lesson outline marks the section you are reading", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await page.goto("/learn/full-oll-overview/");
  await page.waitForTimeout(400);
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const seen = new Set<string>();
  for (let y = 0; y < height - 844; y += 900) {
    await page.evaluate((t) => window.scrollTo(0, t), y);
    await page.waitForTimeout(160);
    // Read through the DOM, not a locator: between two sections NOTHING is in
    // the reading band, so no chip is marked — which is correct, and would make
    // `locator().first().textContent()` throw.
    const state = await page.evaluate(() => ({
      here: document.querySelector(".pagenav .chip.here")?.textContent?.trim() ?? null,
      current: document.querySelectorAll('.pagenav .chip[aria-current="location"]').length,
    }));
    if (state.here) seen.add(state.here);
    // Never two places at once.
    expect(state.current, "two chips claimed to be the current section").toBeLessThan(2);
  }
  expect(seen.size, "the outline never marked more than one section").toBeGreaterThan(2);
});

// The regression the shared module exists to prevent: `scrollIntoView` walks
// every ancestor scrolling box including the document, so revealing a chip
// inside sticky chrome dragged the page backwards 52px at every section
// boundary. /reference has had this gate; now every outline does too.
for (const [name, size] of [
  ["phone", PHONE],
  ["desktop", { width: 1440, height: 900 }],
] as const) {
  test(`scrolling a lesson never moves the page backwards (${name})`, async ({ page }) => {
    await page.setViewportSize(size);
    await page.goto("/learn/full-oll-overview/");
    await page.waitForTimeout(400);
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    let prev = 0;
    for (let y = 0; y < height - size.height; y += 500) {
      await page.evaluate((t) => window.scrollTo(0, t), y);
      await page.waitForTimeout(120);
      const now = await page.evaluate(() => Math.round(window.scrollY));
      expect(now, `the page jumped backwards from ${prev} to ${now}`).toBeGreaterThanOrEqual(
        prev - 5,
      );
      prev = now;
    }
  });
}

test("an outline chip moves focus to its heading, not just the viewport", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await page.goto("/learn/full-oll-overview/");
  await page.locator(".pagenav .chip").nth(3).click();
  await page.waitForTimeout(400);
  const active = await page.evaluate(() => ({
    id: document.activeElement?.id ?? "",
    stillOnChip: document.activeElement?.classList.contains("chip") ?? false,
  }));
  // A keyboard reader continuing to Tab must carry on from the SECTION, not
  // from the next chip — the defect that left ~110 tab stops between a chip and
  // the content it points at on /reference.
  expect(active.stillOnChip, "focus stayed on the chip").toBe(false);
  expect(active.id, "focus must land on the heading the chip names").toBeTruthy();
});

// ── The jump labels the filter indexes are the labels on screen ──────
// `sectionWords()` feeds each section's chip label into every one of its cases'
// search haystacks, so a wrong label is a wrong search index rather than a
// cosmetic slip. tests/search.spec.ts used to carry its own hand-typed copy of
// this map — under a comment claiming it was derived and therefore could not
// drift — and it had drifted four ways: a dead `555-l2e` key, no
// `beginner-triggers`, no `full-pll`, and "4×4 parity" for a chip reading
// "4×4". Both now read src/data/refsections.ts; this checks that registry
// against the rendered page.
test("every rendered section's chip label matches the shared registry", async ({ page }) => {
  await page.goto("/reference/");
  const onPage = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>(".jump .chip[data-jump]")].map((c) => ({
      id: c.dataset.jump!,
      // the chip prints its label then a count in a <span class="n">
      label: (c.childNodes[0]?.textContent ?? "").trim(),
    })),
  );
  expect(onPage.length, "the jump bar must render chips").toBeGreaterThan(5);

  const registry = SECTION_NAV;
  for (const { id, label } of onPage) {
    expect(registry[id], `no registry entry for rendered section "${id}"`).toBeDefined();
    expect(registry[id], `chip for "${id}" reads "${label}"`).toBe(label);
  }
  // …and the registry says what is IN each section, not only what it is
  // called, so the count the heading prints is checked against it. This is the
  // half that could not be gated while the registry held labels alone: the
  // unit corpus had to guess at membership, guessed `CaseDef.group`, and so
  // indexed most of the page under the wrong section name without any gate
  // being able to notice.
  const counts = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>("section[data-section]")].map((sec) => ({
      id: sec.id,
      n: Number(sec.querySelector("[data-section-count]")?.textContent?.replace(/\D/g, "") ?? "-1"),
    })),
  );
  for (const { id, n } of counts) {
    const spec = SECTIONS.find((x) => x.id === id);
    expect(spec, `section #${id} renders but the registry does not list it`).toBeDefined();
    const expected = spec!.members().filter((k) => !isLocked(k)).length;
    expect(n, `#${id} renders ${n} cases, the registry says ${expected}`).toBe(expected);
  }

  // …and every section on the page has an id the registry knows, so a new
  // section cannot ship with an unindexed label.
  const ids = await page.evaluate(() =>
    [...document.querySelectorAll("section[data-section]")].map((s) => s.id),
  );
  for (const id of ids) {
    expect(registry[id], `section #${id} renders but has no jump label`).toBeDefined();
  }
});
