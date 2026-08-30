import { describe, expect, it } from "vitest";

import { CASES, caseById, type CaseDef } from "../src/data/algs";
import { GENERATED_CASES } from "../src/data/fullsets.gen";
import { RICH } from "../src/data/fullsets.rich.gen";
import { filter, haystackFor, matches, normalize } from "../src/lib/search";
import { TRAINER_GROUPS } from "../src/lib/trainer";
import { TAUGHT_444_CASES, isLocked } from "../src/lib/unlocks";

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
 * The extra words /reference feeds each case: its section's jump label plus the
 * trainer's name for the same set. Taken from TRAINER_GROUPS rather than
 * re-typed, so this cannot claim a label the page does not actually render.
 */
const NAV: Record<string, string> = {
  "cross-eo": "Cross",
  "2look-oll-corners": "OLL corners",
  "2look-pll-corners": "PLL corners",
  "2look-pll-edges": "PLL edges",
  "full-oll": "Full OLL",
  "full-f2l": "F2L",
  "444-parity": "4×4 parity",
  "555-l2e": "5×5 L2E",
};
const extraFor = (group: string): string =>
  `${NAV[group] ?? ""} ${TRAINER_GROUPS.find((g) => g.key === group)?.name ?? ""}`;

/**
 * The page's haystacks, built the way the page builds them.
 *
 * Deliberately NOT `ALL_CASES`, which merges a curated entry over its generated
 * twin. /reference renders both — the curated 2-look ROW (whose name is "Ua")
 * and the Full PLL TILE (whose name is "Ua-Perm") — and the difference is not
 * cosmetic: dedupe to the curated name and the corpus contains no "perm" for
 * the U perms at all, so a test built on it would "prove" that "u perm" cannot
 * work while the real page finds both.
 */
const hay = (k: CaseDef, extra: string): string =>
  haystackFor({
    name: k.name,
    recognition: k.recognition ?? RICH[k.id]?.recognition,
    id: k.id,
    group: k.group,
    extra,
  });

/**
 * The corpus keeps its ids, so a test can name the case it expects instead of
 * asserting a number that says nothing about whether the RIGHT case was found.
 *
 * Section membership, not group membership, for the 4×4 parity pair: the page
 * lists them under "4×4 parity" though their generated group is
 * "4x4pll-edges-only", and that section label is the only reason they are
 * findable by the word.
 */
const ENTRY = (k: CaseDef, extra: string) => ({ id: k.id, hay: hay(k, extra) });
const taught444 = (k: CaseDef) => TAUGHT_444_CASES.has(k.id);
const CORPUS = [
  // The two taught 4×4 cases are listed once, by the section that owns them.
  ...CASES.filter((k) => !isLocked(k) && !taught444(k)).map((k) => ENTRY(k, extraFor(k.group))),
  ...GENERATED_CASES.filter((k) => !isLocked(k) && !taught444(k)).map((k) =>
    ENTRY(k, extraFor(k.group)),
  ),
  ...[...TAUGHT_444_CASES]
    .map((id) => caseById.get(id)!)
    .map((k) => ENTRY(k, extraFor("444-parity"))),
];
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
    expect(found("parity").sort()).toEqual(
      ["444.oll-parity", "444.pll.pure-e", "555.l2e-6"].sort(),
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

  it("does not search the algorithm, which would swamp every short token", () => {
    // Deliberate: with the moves in the haystack "R U R'" matched 136 of 138,
    // and every alg's word-initial u and r stopped those tokens discriminating.
    const alg = HAYSTACKS.filter((h) => h.includes("r u r u")).length;
    expect(alg).toBe(0);
  });
});
