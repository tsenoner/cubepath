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
  // `.pagenav`, not `.phase-jump`: the bar moved into the header's second row,
  // so it survives the hero scrolling off a 5,208px page instead of being
  // stranded at y=359. Same assertion, same behaviour, new home.
  await expect(page.locator(".pagenav .chip.here")).toHaveCount(1);
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
    await page.goto(`/glossary/#${id}`);
    await page.waitForTimeout(400);
    const top = await page.locator(`[id="${id}"]`).evaluate((el) => el.getBoundingClientRect().top);
    const bottom = await chromeBottom(page);
    expect(top, `#${id} must not sit under the header`).toBeGreaterThanOrEqual(bottom);
    // …and not a whole header BELOW it either, which is what stacking looked
    // like: clearance is one --space-3 gap, so allow a small tolerance only.
    expect(
      top,
      `#${id} landed ${Math.round(top - bottom)}px below the chrome — anchors stacked`,
    ).toBeLessThan(bottom + 48);
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
  baseURL,
}) => {
  await page.setViewportSize(PHONE);
  // From the SITEMAP, the way stickering.spec.ts enumerates case pages:
  // `astro:content` is a build-time module and cannot be imported here, and a
  // hand-written list of 25 slugs is exactly the staleness this suite exists
  // to catch.
  const sitemap = await (await page.request.get(`${baseURL}/sitemap-0.xml`)).text();
  const slugs = [...sitemap.matchAll(/<loc>[^<]*\/learn\/([^/<]+)\/?<\/loc>/g)].map((m) => m[1]!);
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
    await page.goto(`/learn/full-oll-overview/#${id}`);
    await page.waitForTimeout(200);
    const top = await page.locator(`[id="${id}"]`).evaluate((el) => el.getBoundingClientRect().top);
    expect(top, `#${id} landed under the sticky header`).toBeGreaterThanOrEqual(
      await chromeBottom(page),
    );
  }
});

// The bar must NOT be a completion writer. Crediting a lesson for jumping to
// its own Practice heading would mark it done and hide it from Resume forever —
// the same trap `white-cross.mdx` pointing at /print already documents.
test("no outline chip is tagged as a lesson-completion exit", async ({ page }) => {
  await page.goto("/learn/two-look-oll/");
  expect(await page.locator(".pagenav .chip[data-lesson-advance]").count()).toBe(0);
  expect(await page.locator(".pagenav .chip[data-lesson-next]").count()).toBe(0);
});

// ── The trainer is not a sink ────────────────────────────────────────
// Every other surface points INTO /practice — all 25 lessons and all 129 case
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
