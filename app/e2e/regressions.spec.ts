import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";

/**
 * Regression guards for the three defects the design audit called "outright
 * broken". All three are fixed; none of them was defended, so each could come
 * back silently on the next layout change. This file is the fence:
 *
 *  1. Horizontal overflow at 375px — the worst mobile defect. The page must
 *     never scroll sideways on a phone, in either theme.
 *  2. A visible <img> with no src (or a src that 404s) — Chrome paints its
 *     broken-image glyph plus the alt text, which is what the user screenshot
 *     showed on /practice.
 *  3. `[hidden]` that does not hide. Root cause was `.stage { display: flex }`
 *     out-cascading the origin-weak UA rule for the attribute, which is why
 *     `tokens.css` now carries a global `[hidden] { display: none !important }`.
 *     Asserted for *every* `[hidden]` element on every route, not just for
 *     #review-stage, so the whole class of bug is fenced rather than the one
 *     instance.
 *
 * All three are measured on the SAME page load per (route, theme) — three
 * separate passes would triple an already wide sweep — and every assertion is
 * soft, so one failure does not mask the other two on the same page.
 */

// ── Routes ────────────────────────────────────────────────────────────────
//
// Derived from the built sitemap rather than a hand-written list, so a new
// page is covered the day it ships instead of the day someone remembers to
// add it here. `npx playwright test` serves `dist/` via `astro preview`, so a
// build is already a precondition of this suite running at all.

const DIST = fileURLToPath(new URL("../dist/", import.meta.url));

/**
 * Every route the site publishes, as a path, in sitemap order. Read from every
 * `sitemap-N.xml` rather than just `sitemap-0.xml`, because @astrojs/sitemap
 * shards at 45 000 URLs and a hardcoded shard would quietly stop covering the
 * overflow.
 */
function publishedRoutes(): string[] {
  const shards = readdirSync(DIST).filter((f) => /^sitemap-\d+\.xml$/.test(f));
  if (shards.length === 0) {
    throw new Error(
      `no sitemap-N.xml in ${DIST} — the E2E suite needs a build first ` +
        "(`npx astro build`, or `make ci`).",
    );
  }
  const routes = shards
    .sort()
    .flatMap((shard) => [
      ...readFileSync(join(DIST, shard), "utf8").matchAll(/<loc>([^<]+)<\/loc>/g),
    ])
    .map((m) => m[1])
    .filter((loc): loc is string => typeof loc === "string")
    .map((loc) => new URL(loc).pathname);
  if (routes.length === 0) throw new Error(`${DIST} sitemaps contained no <loc> entries`);
  return routes;
}

/** The page template a route came from: `/case/foo/` and `/case/bar/` share one. */
function template(route: string): string {
  const segments = route.split("/").filter(Boolean);
  const first = segments[0];
  return segments.length > 1 && first !== undefined ? `/${first}/` : route;
}

/**
 * Sampling. The site publishes 218 routes, 185 of them from the single
 * `case/[...id].astro` template — testing all of them twice would spend most
 * of the suite re-proving one layout. So: every route from a template that
 * emits at most `FULL_UNDER` pages is tested in full (that is the home page,
 * /practice, /print, /reference, /c0../c3 and all 25 lessons — every
 * hand-written layout in the app), and the one high-cardinality template is
 * strided down to `SAMPLE_N` pages, first and last always included.
 *
 * The stride is deterministic, so a failure is reproducible; it is computed
 * from the live sitemap, so growth in a sampled group re-spreads the sample
 * instead of leaving new pages permanently outside it.
 */
const FULL_UNDER = 32;
const SAMPLE_N = 12;

function sampledRoutes(): string[] {
  const groups = new Map<string, string[]>();
  for (const route of publishedRoutes()) {
    const key = template(route);
    const bucket = groups.get(key);
    if (bucket) bucket.push(route);
    else groups.set(key, [route]);
  }
  const picked: string[] = [];
  for (const members of groups.values()) {
    if (members.length <= FULL_UNDER) {
      picked.push(...members);
      continue;
    }
    const stride = (members.length - 1) / (SAMPLE_N - 1);
    for (let i = 0; i < SAMPLE_N; i++) {
      const route = members[Math.round(i * stride)];
      if (route !== undefined && !picked.includes(route)) picked.push(route);
    }
  }
  return picked;
}

const ROUTES = sampledRoutes();
const THEMES = ["light", "dark"] as const;
type Theme = (typeof THEMES)[number];

// ── The in-page audit ─────────────────────────────────────────────────────

type Audit = {
  theme: string;
  scrollWidth: number;
  clientWidth: number;
  innerWidth: number;
  /** Innermost elements sticking out past the viewport's right edge. */
  overflowing: string[];
  /** Visible <img> elements with no src, or a src that failed to load. */
  brokenImages: string[];
  /** `[hidden]` elements whose computed display is not `none`. */
  unhidden: string[];
};

/**
 * Runs entirely in the page: one layout read, three verdicts. Returns strings
 * naming the offending elements rather than bare counts, because a bare
 * `expect(0).toBe(1)` inside a 90-case route sweep tells nobody anything.
 */
async function audit(page: Page): Promise<Audit> {
  return page.evaluate(async () => {
    /** A short, human-recognisable path to an element. */
    const label = (el: Element): string => {
      const parts: string[] = [];
      let node: Element | null = el;
      while (node && parts.length < 4) {
        let step = node.tagName.toLowerCase();
        if (node.id) {
          parts.unshift(`${step}#${node.id}`);
          break;
        }
        if (node.classList.length) step += `.${[...node.classList].slice(0, 2).join(".")}`;
        parts.unshift(step);
        node = node.parentElement;
      }
      return parts.join(" > ");
    };

    const rendered = (el: Element): boolean => {
      const rect = el.getBoundingClientRect();
      return el.checkVisibility() && rect.width > 0 && rect.height > 0;
    };

    // (2) Force every lazy image that is on the page to actually fetch, then
    // wait for it to settle. Without this, a below-the-fold <img> whose src
    // 404s never loads during the test and the check silently passes.
    const images = [...document.querySelectorAll("img")].filter(rendered);
    for (const img of images) if (img.loading === "lazy") img.loading = "eager";
    await Promise.all(
      images.map(
        (img) =>
          new Promise<void>((resolve) => {
            if (img.complete) return resolve();
            img.addEventListener("load", () => resolve(), { once: true });
            img.addEventListener("error", () => resolve(), { once: true });
            setTimeout(resolve, 5000);
          }),
      ),
    );
    const brokenImages = images
      .filter((img) => !img.currentSrc || !img.getAttribute("src") || img.naturalWidth === 0)
      .map(
        (img) =>
          `${label(img)} [src=${JSON.stringify(img.getAttribute("src"))}, ` +
          `naturalWidth=${img.naturalWidth}, alt=${JSON.stringify(img.alt)}]`,
      );

    // (1) Horizontal overflow. Report the innermost culprits — an outer
    // wrapper is stretched *by* the offender, so naming it sends the reader
    // to the wrong file.
    await document.fonts.ready;
    const limit = document.documentElement.clientWidth;
    // A deliberately side-scrolling strip (the /reference jump bar) and a
    // fixed-position overlay both put boxes past the viewport edge without
    // making the *document* scroll. Only an element with an unbroken chain of
    // non-clipping, non-fixed ancestors can widen the page.
    const widensThePage = (el: Element): boolean => {
      for (let n: Element | null = el; n && n !== document.body; n = n.parentElement) {
        const cs = getComputedStyle(n);
        if (cs.position === "fixed") return false;
        if (n === el) continue;
        if (["auto", "scroll", "hidden", "clip"].includes(cs.overflowX)) return false;
      }
      return true;
    };
    const past = [...document.querySelectorAll("body *")].filter((el) => {
      if (!rendered(el) || !widensThePage(el)) return false;
      const rect = el.getBoundingClientRect();
      return rect.right > limit + 1 || rect.left < -1;
    });
    const overflowing = past
      .filter((el) => !past.some((other) => other !== el && el.contains(other)))
      .slice(0, 6)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return `${label(el)} [left=${Math.round(rect.left)}, right=${Math.round(rect.right)}, viewport=${limit}]`;
      });

    // (3) `[hidden]` must hide. `hidden="until-found"` is excluded on
    // purpose: it is *defined* to keep a rendered box (content-visibility),
    // so flagging it would be wrong rather than strict.
    const unhidden = [...document.querySelectorAll("[hidden]")]
      .filter((el) => el.getAttribute("hidden") !== "until-found")
      .filter((el) => getComputedStyle(el).display !== "none")
      .map(
        (el) => `${label(el)} [display=${getComputedStyle(el).display}, rendered=${rendered(el)}]`,
      );

    return {
      theme: document.documentElement.dataset["theme"] ?? "(none)",
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      innerWidth: window.innerWidth,
      overflowing,
      brokenImages,
      unhidden,
    };
  });
}

/**
 * Pin the theme the way a returning visitor has it pinned — through the
 * localStorage key the blocking script in Base.astro reads — rather than by
 * stamping the attribute ourselves, so the test exercises the real path.
 */
async function pinTheme(page: Page, theme: Theme): Promise<void> {
  await page.addInitScript((t) => {
    try {
      localStorage.setItem("cubepath.theme", t);
    } catch {
      /* Storage denied — the page falls back to the OS theme. */
    }
  }, theme);
}

// ── The sweep ─────────────────────────────────────────────────────────────

test.describe("mobile regressions — 375px, both themes", () => {
  // 375px is the narrowest phone still in wide use (iPhone SE/12 mini/13 mini);
  // anything that fits here fits every larger handset.
  test.use({ viewport: { width: 375, height: 812 }, serviceWorkers: "block" });
  // Playwright runs a file's tests serially in one worker by default, and this
  // sweep is ~90 page loads.
  test.describe.configure({ mode: "parallel" });

  for (const theme of THEMES) {
    for (const route of ROUTES) {
      test(`375px ${theme}: ${route} — no h-scroll, no broken img, [hidden] hides`, async ({
        page,
      }) => {
        await pinTheme(page, theme);
        const res = await page.goto(route);
        expect(res?.status(), `${route} did not resolve`).toBeLessThan(400);
        const where = `${route} @375px in ${theme} theme`;

        const a = await audit(page);

        // A theme that never applied would make "both themes" a lie.
        expect(a.theme, `${where}: theme never applied to <html data-theme>`).toBe(theme);

        // (1) No horizontal scroll.
        expect
          .soft(
            a.overflowing,
            `${where}: element(s) stick out past the 375px viewport — this is the mobile ` +
              `h-scroll regression. Offenders (innermost first):`,
          )
          .toEqual([]);
        expect
          .soft(
            a.scrollWidth,
            `${where}: the page scrolls horizontally — documentElement.scrollWidth ` +
              `${a.scrollWidth} > clientWidth ${a.clientWidth} (innerWidth ${a.innerWidth}).`,
          )
          .toBeLessThanOrEqual(a.clientWidth);
        expect
          .soft(
            a.scrollWidth,
            `${where}: scrollWidth ${a.scrollWidth} exceeds innerWidth ${a.innerWidth}.`,
          )
          .toBeLessThanOrEqual(a.innerWidth);

        // (2) No visible <img> without a working src.
        expect
          .soft(
            a.brokenImages,
            `${where}: visible <img> with a missing or non-loading src — Chrome paints its ` +
              `broken-image glyph and the alt text here. Offenders:`,
          )
          .toEqual([]);

        // (3) `[hidden]` actually hides.
        expect
          .soft(
            a.unhidden,
            `${where}: element(s) carrying [hidden] compute to a display other than none — ` +
              `an author rule is out-cascading tokens.css's [hidden] { display: none !important }. ` +
              `Offenders:`,
          )
          .toEqual([]);
      });
    }
  }
});

// ── The exact screenshot the user reported ────────────────────────────────

test.describe("practice: the reported defect, specifically", () => {
  test.use({ serviceWorkers: "block" });

  test("review stage and its diagram are invisible on a fresh /practice load", async ({ page }) => {
    // Fresh = no stored practice state. A new context has none, but say so.
    await page.goto("/practice/");
    await expect(page.getByTestId("scramble")).not.toHaveText("…", { timeout: 15_000 });

    const stage = page.locator("#review-stage");
    await expect(stage, "#review-stage is visible on a fresh load — the reported bug").toBeHidden();
    await expect(
      page.locator("#review-img"),
      "#review-img (the src-less <img> from the report) is visible on a fresh load",
    ).toBeHidden();
    await expect(
      page.locator("#case-img"),
      "#case-img has no src until a case is revealed and must stay hidden",
    ).toBeHidden();

    // Belt and braces: the attribute must be doing the hiding, not luck.
    const display = await stage.evaluate((el) => getComputedStyle(el).display);
    expect(display, "#review-stage carries [hidden] but does not compute to display:none").toBe(
      "none",
    );
  });
});
