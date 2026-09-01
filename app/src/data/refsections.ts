/**
 * The short label /reference prints on each section's jump chip.
 *
 * This exists because the same strings were needed in two places and the second
 * copy drifted. `tests/search.spec.ts` carried a hand-written map whose own
 * comment claimed it was "taken from TRAINER_GROUPS rather than re-typed, so
 * this cannot claim a label the page does not actually render" — and it was
 * re-typed, and it had drifted four ways against the ten sections the page
 * renders: it kept `555-l2e` (renamed to `555-parity` when the 5×5 set was
 * cut), it was missing `beginner-triggers` and `full-pll` entirely, and it
 * called `444-parity` "4×4 parity" where the chip says "4×4". So the filter was
 * gated against a corpus the page never renders, which is precisely what that
 * comment promised was impossible.
 *
 * The label is part of what the filter matches on — `sectionWords()` feeds it
 * into every case's haystack, which is what makes a case findable by the
 * heading a reader can see above it — so a wrong label here is a wrong search
 * index, not a cosmetic slip.
 *
 * Ids include the two locked 4×4 sets. `lib/unlocks.ts` decides what is
 * rendered; this only says what a section is CALLED, and keeping the hidden
 * ones listed means unlocking a set does not also need an edit here.
 */
export const SECTION_NAV: Record<string, string> = {
  "beginner-triggers": "Triggers",
  "cross-eo": "Cross",
  "2look-oll-corners": "OLL corners",
  "2look-pll-corners": "PLL corners",
  "2look-pll-edges": "PLL edges",
  "full-oll": "Full OLL",
  "full-f2l": "F2L",
  "full-pll": "Full PLL",
  "444-parity": "4×4",
  "444-oll": "4×4 OLL",
  "444-pll": "4×4 PLL",
  "555-parity": "5×5",
};

/** The chip label for a section id. Throws rather than shipping a blank chip. */
export function sectionNav(id: string): string {
  const nav = SECTION_NAV[id];
  if (nav === undefined) throw new Error(`refsections: no jump label for section "${id}"`);
  return nav;
}
