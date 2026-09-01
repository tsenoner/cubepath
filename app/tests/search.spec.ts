import { describe, expect, it } from "vitest";

import { caseHaystack } from "../src/lib/casesearch";
import { filter, matches, normalize } from "../src/lib/search";
import { SECTIONS, sectionWords } from "../src/data/refsections";
import { isLocked } from "../src/lib/unlocks";

/**
 * The /reference filter, gated against the real dataset.
 *
 * Every expectation below is a query a cuber actually types, and the ones in
 * FINDS_EXACTLY all returned ZERO before lib/search.ts existed — the filter was
 * `.includes()` over name + cue + id, so a hyphen and a × were load-bearing.
 * The table is the contract: it fails if the matcher gets looser (a query that
 * should name one case starts naming twenty) or tighter (a query that should
 * cast wide stops finding anything).
 */

/**
 * The page's haystacks, built the way the page builds them.
 *
 * SECTION-DRIVEN, exactly like the page: walk the visible sections in order,
 * take each one's members, and give every one of them that section's words.
 * This used to walk the CASE LISTS instead and key the words on `CaseDef.group`
 * — a recognition grouping in a different namespace — so most of the corpus
 * carried "oll dot" where the page carries "Full OLL", and the gate written to
 * stop a re-typed label map from drifting could not see a wrong label on any
 * full set. Membership lives in data/refsections.ts now, so there is nothing
 * left here to guess.
 *
 * Deliberately NOT deduped to `ALL_CASES`, because the page is not: it renders
 * the curated 2-look ROW (whose name is "Ua") and the Full PLL TILE (whose name
 * is "Ua-Perm"), and the difference is not cosmetic. Dedupe to the curated name
 * and the corpus contains no "perm" for the U perms at all, so a test built on
 * it would "prove" that "u perm" cannot work while the real page finds both.
 */

/**
 * The corpus keeps its ids, so a test can name the case it expects instead of
 * asserting a number that says nothing about whether the RIGHT case was found.
 */
const CORPUS = SECTIONS.filter((s) => !isLocked(s.id)).flatMap((s) =>
  s
    .members()
    .filter((k) => !isLocked(k))
    .map((k) => ({ id: k.id, hay: caseHaystack(k, sectionWords(s.id)) })),
);
const HAYSTACKS = CORPUS.map((e) => e.hay);

const found = (q: string): string[] =>
  filter(HAYSTACKS, q)
    .map((hit, i) => (hit ? CORPUS[i]!.id : null))
    .filter((x): x is string => x !== null);
const hits = (q: string): number => found(q).length;

describe("normalize", () => {
  it("folds the punctuation the dataset and the keyboard disagree about", () => {
    // The dataset writes "4×4"; a keyboard types "4x4".
    expect(normalize("Ba (4×4 PLL)")).toBe("ba 4x4 pll");
    // A hyphen is a word break, not a character to type.
    expect(normalize("T-Perm")).toBe("t perm");
    // Apostrophes are dropped, not spaced, so R' and R share a token.
    expect(normalize("R U R' U'")).toBe("r u r u");
  });
});

describe("matches", () => {
  it("requires every token, in any order", () => {
    expect(matches("t perm pll t", "t perm")).toBe(true);
    expect(matches("t perm pll t", "perm t")).toBe(true);
    expect(matches("t perm pll t", "t perm sune")).toBe(false);
  });

  it("keeps long tokens as substrings, so fragments of prose still match", () => {
    // "light" inside "headlights" and "perm" inside "T-Perm" are the two
    // commonest real queries; anchoring them to a word start would kill both.
    expect(matches("two headlights on the left", "light")).toBe(true);
    expect(matches("t perm", "perm")).toBe(true);
  });

  it("will not let a one-character token match everything", () => {
    // Plain substring here is what made "t perm" match all 25 perms.
    expect(matches("ua perm", "u")).toBe(false);
    expect(matches("ua perm", "u", true)).toBe(true);
  });
});

describe("filter over the real case list", () => {
  it("finds exactly one case for a query that names one", () => {
    // "t perm" is the single likeliest query on the page. Two hits, not one,
    // is correct: the T-Perm is deliberately listed twice, once as a curated
    // 2-look row and once as a Full PLL tile.
    expect(hits("t perm")).toBe(hits("T-Perm"));
    expect(hits("t perm")).toBeLessThanOrEqual(2);
    expect(hits("anti sune")).toBe(1);
  });

  it("finds the sets a reader names off the screen", () => {
    // Every one of these returned 0 before.
    for (const q of ["4x4", "5x5", "awkward", "u perm", "t perm", "anti sune"]) {
      expect(hits(q), `"${q}" must find something`).toBeGreaterThan(0);
    }
  });

  it("finds every parity case the course teaches, not one of them", () => {
    // "parity" used to return 1 of 3, so the 5x5 case read as missing from the
    // site. Named, not counted — the point is WHICH cases come back.
    //
    // FOUR, not three. `444.edge-flip` is rendered in the `444-parity` section
    // and so carries that section's words, which is the whole mechanism that
    // makes the 5x5 case findable at all — and the built page has always
    // returned it here. This corpus asserted three because it keyed the words
    // on `CaseDef.group` instead of on the section, and so was gated against a
    // page that does not exist. It is a fair result rather than an over-match:
    // the flip is one of the three rows a reader typing "parity" is shown, and
    // the section it sits in is exactly what they asked for.
    expect(found("parity").sort()).toEqual(
      ["444.edge-flip", "444.oll-parity", "444.pll.pure-e", "555.l2e-6"].sort(),
    );
  });

  it("finds a case by a name only the site's other surfaces give it", () => {
    // 555.l2e-6 is called "L2E 6" and cued "One edge group flipped"; the word
    // "parity" is nowhere in the case. The lesson, the trainer and every cuber
    // call it edge parity, and the trainer's name for the set is what carries
    // that into the haystack. This is the whole reason `extra` exists.
    expect(found("edge parity")).toContain("555.l2e-6");
    expect(found("5x5")).toContain("555.l2e-6");
  });

  it("keeps a broad query broad", () => {
    expect(hits("perm")).toBeGreaterThan(15);
    expect(hits("headlights")).toBeGreaterThan(5);
  });

  it("returns everything for an empty query and nothing for nonsense", () => {
    expect(hits("")).toBe(CORPUS.length);
    expect(hits("   ")).toBe(CORPUS.length);
    expect(hits("zzzzqqq")).toBe(0);
  });

  it("widens only when the strict pass finds nothing", () => {
    // "u" is not a whole word anywhere (the cases are Ua and Ub), so the loose
    // pass runs; "t" IS a whole word (pll.t normalizes to "pll t"), so it does
    // not, and "t" stays specific instead of matching every t-word in a cue.
    expect(hits("u perm")).toBeGreaterThan(0);
    expect(hits("t perm")).toBeLessThan(hits("perm"));
  });

  it("does not let a set's own size become a searchable token", () => {
    // The trainer calls them "Full OLL (57)", "F2L (41)", "Full PLL (all 21)".
    // Feeding those names verbatim put the count into every member's haystack,
    // so "57" matched all 57 OLL cases instead of OLL 57 — and the OLL cases are
    // named by number, which makes that the query the set is most searched by.
    expect(found("57")).toContain("oll.57");
    expect(hits("57")).toBeLessThanOrEqual(4);
    expect(hits("41")).toBeLessThanOrEqual(4);
    expect(hits("21")).toBeLessThanOrEqual(6);
  });

  it("does not search the algorithm, which would swamp every short token", () => {
    // Deliberate: with the moves in the haystack "R U R'" matches 100 of 142,
    // and every alg's word-initial u and r stopped those tokens discriminating.
    const alg = HAYSTACKS.filter((h) => h.includes("r u r u")).length;
    expect(alg).toBe(0);
  });
});
