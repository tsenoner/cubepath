/**
 * What /reference is made of: the sections, in order, each with the short label
 * its jump chip prints and the cases it renders.
 *
 * WHY MEMBERSHIP LIVES HERE AND NOT IN THE PAGE. This started as a label-only
 * map, and a label-only map cannot be gated. `tests/search.spec.ts` needs the
 * words the page feeds each case's search haystack, which are the words of the
 * SECTION rendering it; with only labels exported it had to guess at membership
 * and keyed them on `CaseDef.group` instead — a recognition grouping
 * ("oll-dot", "f2l-connected-pairs") in a different namespace entirely. For the
 * three grid sections that is most of the page's entries carrying "oll dot"
 * in the corpus where the page carries "Full OLL", so the gate written to stop
 * a re-typed label map from drifting was itself blind to a wrong label on every
 * full set. The registry now says what a section IS, and the page and the spec
 * both build from it, so the corpus and the page cannot disagree.
 *
 * The page keeps the WORDING — titles and blurbs — because that is prose, not
 * structure; it supplies one entry per id here and fails the build if the two
 * lists stop matching.
 *
 * Ids include the two locked 4×4 sets. `lib/unlocks.ts` decides what is
 * rendered; this only says what a section is and what is in it, so unlocking a
 * set does not also need an edit here.
 */
import { CASES, caseById, type CaseDef } from "./algs";
import { GENERATED_CASES } from "./fullsets.gen";
import { setName } from "../lib/trainer";
import { TAUGHT_444_CASES } from "../lib/unlocks";

export interface SectionSpec {
  /** URL fragment, and the trainer-group / phase key the section is named for. */
  id: string;
  /**
   * Short form, for the jump bar — mirroring `PhaseInfo.nav` on the course
   * index and for the same reason: ten full titles ("Corner Orientation —
   * 2-Look OLL") make a chip strip several rows deep on a phone, which pushes
   * the first case off the screen the bar exists to save you scrolling to.
   */
  nav: string;
  /** The cases this section renders, in dataset order. */
  members: () => CaseDef[];
}

/** Curated course cases carrying this section's own key. */
const curated = (id: string) => (): CaseDef[] => CASES.filter((k) => k.group === id);
const gen = (test: (k: CaseDef) => boolean) => (): CaseDef[] => GENERATED_CASES.filter(test);

export const SECTIONS: SectionSpec[] = [
  {
    id: "beginner-triggers",
    nav: "Beginner",
    // Course membership: five groups, one section. The triggers, the inserts,
    // the edge swap, the corner cycle and the corner twists sit at different
    // stages of the ladder, but a reader looking up "the beginner algorithms"
    // wants one list, not five. The prefix is the contract — every group in
    // algs.ts's beginner block carries it — so a group added there is rendered
    // here without a second edit. The id keeps its original name: it is a URL
    // fragment, and a bookmark or a printed link to it should keep working.
    members: () => CASES.filter((k) => k.group.startsWith("beginner-")),
  },
  { id: "cross-eo", nav: "Cross", members: curated("cross-eo") },
  { id: "2look-oll-corners", nav: "OLL corners", members: curated("2look-oll-corners") },
  { id: "2look-pll-corners", nav: "PLL corners", members: curated("2look-pll-corners") },
  { id: "2look-pll-edges", nav: "PLL edges", members: curated("2look-pll-edges") },
  { id: "full-oll", nav: "Full OLL", members: gen((k) => /^oll\.\d+$/.test(k.id)) },
  { id: "full-f2l", nav: "F2L", members: gen((k) => k.phase === "full-f2l") },
  { id: "full-pll", nav: "Full PLL", members: gen((k) => k.id.startsWith("pll.")) },
  {
    id: "444-parity",
    nav: "4×4",
    // Course membership, not data membership: the two PLL-parity faces were
    // generated into "4x4pll-edges-only" alongside cases the course does not
    // teach, but the 4×4 lesson teaches both of them. The edge flip is a
    // curated entry with no set of its own — it is a mid-pairing tool, so it
    // belongs to no case list, which is exactly why it had no row anywhere.
    members: () => [
      caseById.get("444.edge-flip")!,
      ...[...TAUGHT_444_CASES].map((id) => caseById.get(id)!),
    ],
  },
  { id: "444-oll", nav: "4×4 OLL", members: gen((k) => k.group.startsWith("4x4oll-")) },
  { id: "444-pll", nav: "4×4 PLL", members: gen((k) => k.group.startsWith("4x4pll-")) },
  { id: "555-parity", nav: "5×5", members: gen((k) => k.phase === "555") },
];

/** The jump label for every section id. Derived, so there is no second list. */
export const SECTION_NAV: Record<string, string> = Object.fromEntries(
  SECTIONS.map((s) => [s.id, s.nav]),
);

/** The chip label for a section id. Throws rather than shipping a blank chip. */
export function sectionNav(id: string): string {
  const nav = SECTION_NAV[id];
  if (nav === undefined) throw new Error(`refsections: no jump label for section "${id}"`);
  return nav;
}

/**
 * The words a section is known by beyond its own heading: the jump label plus
 * the trainer's name for the same set. Fed to `haystackFor`'s `extra`, so a
 * reader who types a heading they can see finds the cases under it.
 *
 * ONE definition, because this is the composition that drifted last time. The
 * previous fix imported the label map into `tests/search.spec.ts` but left the
 * COMPOSITION duplicated there, so the page could still change what it feeds
 * the filter with the corpus none the wiser.
 *
 * The trainer name is not redundant with the label: it is the site's OTHER
 * public name for the set, printed on every lesson's "Drill …" button, and in
 * one case it is the only place the site writes down what the set is called.
 * The single 5×5 case is `L2E 6`, cued "One edge group flipped" — the word
 * "parity" appears nowhere in the case, though the lesson, the trainer and
 * every cuber alive call it edge parity.
 */
export function sectionWords(id: string): string {
  return `${sectionNav(id)} ${setName(id)}`;
}

/**
 * The DOM id a case is addressed by on /reference: its id with dots replaced by
 * dashes, so `#555-l2e-6` and `#444-oll-parity` both resolve.
 *
 * Derived in one place for the same reason `phaseAnchor()` is (see
 * data/phases.ts): the page that WRITES the anchor and the case page whose
 * breadcrumb LINKS to it cannot disagree. They each hand-wrote this rule, and a
 * change to either produced a dead fragment — a silent scroll to the top of a
 * 12,000px page, not an error.
 */
export function caseAnchor(id: string): string {
  return id.replace(/\./g, "-");
}

/** A link into /reference: a whole section by key, or one case by id. */
export function referenceHref(anchor: string): string {
  return `/reference/#${anchor}`;
}
