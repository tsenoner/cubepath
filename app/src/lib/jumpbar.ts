/**
 * The behaviour half of an in-page jump bar, shared by every surface that has
 * one: /reference's section strip and the `pagenav` outline on /, /glossary and
 * all 25 lessons.
 *
 * This is a MOVE, not a rewrite. Every line below was proven on /reference and
 * is gated by `e2e/nav.spec.ts`; the outline bars shipped as plain anchors
 * precisely so that this machinery could be shared rather than re-derived, and
 * the two traps it encodes are both regressions this repo actually shipped.
 *
 * TRAP ONE — `scrollIntoView` is not usable here. It walks EVERY ancestor
 * scrolling box, and the last one is the document. A chip lives inside sticky
 * chrome whose rendered box sits above the optimal viewing region that
 * `html { scroll-padding-block-start }` establishes, so the browser judges the
 * chip out of view and scrolls the DOCUMENT to reveal it — and because the bar
 * is sticky the chip never moves, so it never converges. Measured at -52px per
 * section boundary, all the way down a 9,000px page, in Chromium and WebKit
 * alike. `revealChip` therefore sets `scrollLeft`/`scrollTop` on the bar and
 * touches no ancestor.
 *
 * TRAP TWO — the observer must clear the current-chip marking BEFORE its early
 * return. A filter that empties the page makes every section `display: none`,
 * so nothing intersects; an early return there stranded `aria-current` on a
 * chip that was simultaneously `aria-disabled` and announced "no matches" —
 * read out as both the place you are and a place you cannot go.
 */

export interface JumpBarOptions {
  /** The scrolling strip (phone) or column (desktop) holding the chips. */
  bar: HTMLElement;
  /** The chips, in document order. Anchors: the href IS the destination. */
  chips: HTMLAnchorElement[];
}

/**
 * The id a chip points at. Read off the href rather than taken from the caller,
 * because the href is the contract the markup already honours for a reader with
 * no JavaScript — /reference's chips carried a `data-jump` holding the same
 * string a second time, purely to hand it back here.
 */
function chipId(chip: HTMLAnchorElement): string {
  return decodeURIComponent(chip.hash.slice(1));
}

/**
 * A chip the page has disabled must never be marked as where you are.
 * /reference disables the chips whose section its filter emptied.
 *
 * `aria-disabled`, which is what the click handler below already tests and what
 * the filter already writes. The caller used to pass a predicate over a `.off`
 * CLASS set on the same line as the attribute, so the module held two notions
 * of disabled and only one of them was the one it announced.
 */
function isDisabled(chip: HTMLAnchorElement): boolean {
  return chip.getAttribute("aria-disabled") === "true";
}

/**
 * The height of the one sticky box, right now.
 *
 * `.site-header` is that box on every route — a page that needs its own bar
 * renders it into Header's `pagenav` slot, as a second row inside it — so this
 * is the whole of the chrome wherever a jump bar exists. At >=1100px the
 * outline is `position: fixed` and OUT of the header, and the header is one
 * thin row again; reading the live height covers both without a breakpoint in
 * JavaScript. Three places wrote this same line: both jump bars, and
 * /reference's "scroll the first match into view" arithmetic.
 */
export function chromeHeight(): number {
  return document.querySelector<HTMLElement>(".site-header")?.offsetHeight ?? 0;
}

/**
 * Bring a chip into view along the BAR, and only the bar.
 *
 * Handles both axes because the same bar is a horizontal strip below 561px and
 * a vertical column at >=1100px. Each branch is a no-op when that axis does not
 * overflow — which is the common case at desktop widths, where every chip is
 * already visible.
 */
function revealChip(bar: HTMLElement, chip: HTMLElement): void {
  const pad = 8;
  const barBox = bar.getBoundingClientRect();
  const box = chip.getBoundingClientRect();
  if (bar.scrollWidth > bar.clientWidth) {
    if (box.left < barBox.left) bar.scrollLeft += box.left - barBox.left - pad;
    else if (box.right > barBox.right) bar.scrollLeft += box.right - barBox.right + pad;
  }
  if (bar.scrollHeight > bar.clientHeight) {
    if (box.top < barBox.top) bar.scrollTop += box.top - barBox.top - pad;
    else if (box.bottom > barBox.bottom) bar.scrollTop += box.bottom - barBox.bottom + pad;
  }
}

/**
 * Move focus to a section, not just the viewport.
 *
 * A chip used to move the viewport and leave focus on itself, so the next Tab
 * went to the next chip: for a keyboard reader the only route into /reference's
 * Full PLL tiles was ~110 tab stops. `tabindex="-1"` is added on demand because
 * a lesson heading is not focusable on its own — /reference's sections carry it
 * in the markup, an `<h2>` does not, and a jump that does not move focus is
 * only half a jump. `html`'s scroll-padding does the rest.
 */
function focusTarget(id: string): void {
  // getElementById, never querySelector("#" + id): six shipped heading ids
  // begin with a digit, which are legal fragments and illegal selectors.
  const el = document.getElementById(id);
  if (!el) return;
  if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
  el.focus();
}

/**
 * Mark the chips whose section the page has filtered away.
 *
 * A chip pointing at a `display: none` section is a dead link: pressing it
 * rewrites the URL fragment and moves nothing, with no feedback at all, and
 * `focusTarget` cannot focus a hidden element either. /reference fixed that —
 * and kept the fix in its own page script, twelve lines of `aria-disabled`,
 * `tabIndex` and class toggling that the NEXT filtered page could not inherit.
 * /glossary is that page: it hides whole groups on a query and shipped live
 * chips over them.
 *
 * Here instead, so any bar over any filter gets it by construction. Call it
 * after the filter has set `hidden`.
 */
export function markEmptySections(bar: HTMLElement): void {
  for (const chip of bar.querySelectorAll<HTMLAnchorElement>("a[href^='#']")) {
    const target = document.getElementById(chipId(chip));
    const off = target !== null && target.hidden;
    chip.classList.toggle("off", off);
    // All three agree, or the appearance and the semantics disagree: out of the
    // tab order, out of the pointer's reach (`a.chip.off` in tokens.css) and
    // announced.
    chip.setAttribute("aria-disabled", String(off));
    chip.tabIndex = off ? -1 : 0;
    const flag = chip.querySelector<HTMLElement>("[data-jump-empty]");
    if (flag) flag.hidden = !off;
  }
}

/**
 * Mark where the reader is, keep that chip in view, and make a chip a real
 * jump. Safe to call when the page has no bar or the browser has no
 * IntersectionObserver — it simply does less.
 */
export function wireJumpBar(opts: JumpBarOptions): void {
  const { bar, chips } = opts;
  if (chips.length === 0) return;

  const chipFor = new Map(chips.map((c) => [chipId(c), c] as const));
  const sections = chips
    .map((c) => document.getElementById(chipId(c)))
    .filter((el): el is HTMLElement => el !== null);

  // ── Jump = go there, not just scroll there ─────────────────────────
  bar.addEventListener("click", (e) => {
    const link = (e.target as HTMLElement | null)?.closest<HTMLAnchorElement>("a[href^='#']");
    if (!link || link.getAttribute("aria-disabled") === "true") return;
    // Let the browser do the navigation and the scroll; only take the focus.
    requestAnimationFrame(() => focusTarget(decodeURIComponent(link.hash.slice(1))));
  });
  window.addEventListener("hashchange", () => {
    const id = decodeURIComponent(location.hash.slice(1));
    if (id && chipFor.has(id)) focusTarget(id);
  });

  // ── Which section am I in? ─────────────────────────────────────────
  if (sections.length === 0 || !("IntersectionObserver" in window)) return;

  // Suppress the auto-scroll for a moment after the reader pans the bar
  // themselves, so it cannot yank the chips out from under their thumb.
  let pannedUntil = 0;
  bar.addEventListener("scroll", () => (pannedUntil = performance.now() + 1000), {
    passive: true,
  });

  const spy = new IntersectionObserver(
    (records) => {
      // Clear BEFORE the early return — see TRAP TWO above.
      for (const c of chips) {
        c.classList.remove("here");
        c.removeAttribute("aria-current");
      }
      const hit = records.find((r) => r.isIntersecting);
      if (!hit) return;
      const chip = chipFor.get(hit.target.id);
      if (!chip || isDisabled(chip)) return;
      chip.classList.add("here");
      chip.setAttribute("aria-current", "location");
      if (performance.now() > pannedUntil) revealChip(bar, chip);
    },
    // Top edge at the bottom of the sticky chrome, bottom edge 55% up the
    // viewport: the current section is the one occupying the band you read.
    { rootMargin: `-${Math.round(chromeHeight())}px 0px -55% 0px` },
  );
  for (const s of sections) spy.observe(s);
}

/**
 * Wire the `pagenav` outline on whatever page is currently loaded.
 *
 * The whole body lives here rather than inline in JumpBar.astro's `<script>`
 * so it is type-checked as ordinary TypeScript. (It also sidesteps an
 * `astro check` quirk where a multi-line client script mis-attributes its
 * inference failures to the component's frontmatter, reporting `Props` as
 * unused and every markup callback as implicitly `any`.)
 */
export function wirePageNav(): void {
  // One bar per page by construction — it is rendered into Header's single
  // `pagenav` slot. The chips carry no `data-jump`: their href IS the id, which
  // is the contract the markup already honours for a reader with no JavaScript.
  const bar = document.querySelector<HTMLElement>(".pagenav");
  if (!bar) return;
  wireJumpBar({ bar, chips: [...bar.querySelectorAll<HTMLAnchorElement>("a[href^='#']")] });
}
