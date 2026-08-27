import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * The product is teaching, so the pages have to be readable by assistive tech,
 * not only by a browser. Axe is the deterministic subset of accessibility worth
 * gating: it runs on the same real build the rest of the E2E suite drives, and
 * it never fails for reasons unrelated to the page (no scores, no budgets).
 *
 * Only `serious` and `critical` findings fail — `minor`/`moderate` are advisory
 * and would turn a colour tweak into a red gate.
 */
const PAGES = [
  ["/", "home / course ladder"],
  ["/learn/notation/", "a lesson page (MDX + twisty players)"],
  ["/practice/", "the keyboard-driven trainer"],
  ["/reference/", "the full case reference"],
] as const;

for (const [path, what] of PAGES) {
  test(`no serious a11y violations: ${path} — ${what}`, async ({ page }) => {
    await page.goto(path);
    const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    const serious = violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(
      serious.map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target).join(" | ")}`),
    ).toEqual([]);
  });
}
