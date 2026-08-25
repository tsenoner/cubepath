/**
 * Machine-verification of every published algorithm on the cubing.js kpuzzle.
 * A case's primary algorithm must solve the state its own inverse creates.
 * This is the CI gate that makes a wrong algorithm a build failure.
 */
import { describe, expect, test } from "vitest";
import { Alg } from "cubing/alg";
import { puzzles } from "cubing/puzzles";
import type { KPuzzle } from "cubing/kpuzzle";

import { ALL_CASES, CASES, caseById, primaryAlg } from "../src/data/algs";
import { CASE_SCRAMBLES } from "../src/data/fullsets.gen";
import { RICH } from "../src/data/fullsets.rich.gen";
import { groupSize } from "../src/lib/trainer";

const kpuzzleCache = new Map<string, Promise<KPuzzle>>();

function kpuzzleFor(puzzle: string): Promise<KPuzzle> {
  let p = kpuzzleCache.get(puzzle);
  if (!p) {
    p = puzzles[puzzle]!.kpuzzle();
    kpuzzleCache.set(puzzle, p);
  }
  return p;
}

async function algSolvesItsInverse(puzzle: string, moves: string): Promise<boolean> {
  const kpuzzle = await kpuzzleFor(puzzle);
  const alg = new Alg(moves);
  return kpuzzle
    .defaultPattern()
    .applyAlg(alg.invert())
    .applyAlg(alg)
    .experimentalIsSolved({ ignorePuzzleOrientation: true, ignoreCenterOrientation: true });
}

describe("every case's algorithms are valid and solve their own case", () => {
  for (const def of ALL_CASES) {
    for (const [i, variant] of def.algs.entries()) {
      test(`${def.id} alg[${i}] (${variant.moves})`, async () => {
        // Parses as a real alg for this puzzle (throws on unknown moves)…
        const kpuzzle = await kpuzzleFor(def.puzzle);
        kpuzzle.algToTransformation(new Alg(variant.moves));
        // …and round-trips to solved.
        expect(await algSolvesItsInverse(def.puzzle, variant.moves)).toBe(true);
      });
    }
  }
});

describe("every rich alternate algorithm is valid and solves its case", () => {
  for (const [id, rich] of Object.entries(RICH)) {
    const def = caseById.get(id);
    for (const [i, variant] of rich.alternates.entries()) {
      test(`${id} alt[${i}] (${variant.moves})`, async () => {
        expect(def, `RICH id ${id} missing from ALL_CASES`).toBeTruthy();
        const kpuzzle = await kpuzzleFor(def!.puzzle);
        kpuzzle.algToTransformation(new Alg(variant.moves));
        expect(await algSolvesItsInverse(def!.puzzle, variant.moves)).toBe(true);
      });
    }
  }
});

describe("dataset invariants", () => {
  test("ids are unique", () => {
    const ids = ALL_CASES.map((k) => k.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  test("every case has exactly one primary algorithm", () => {
    for (const def of ALL_CASES) {
      expect(def.algs.filter((a) => a.primary).length, def.id).toBe(1);
      expect(primaryAlg(def)).toBeTruthy();
    }
  });

  test("prereqs reference existing cases", () => {
    const ids = new Set(ALL_CASES.map((k) => k.id));
    for (const def of ALL_CASES) {
      for (const p of def.prereqs ?? []) {
        expect(ids.has(p), `${def.id} prereq ${p}`).toBe(true);
      }
    }
  });

  test("full OLL/PLL coverage present", () => {
    expect(ALL_CASES.filter((k) => k.id.startsWith("oll.")).length).toBe(57);
    expect(ALL_CASES.filter((k) => k.id.startsWith("pll.")).length).toBe(21);
  });

  test("full-set trainer groups cover the whole sets", () => {
    expect(groupSize("full-oll")).toBe(57);
    expect(groupSize("full-pll")).toBe(21);
  });

  test("curated course cases survive the merge", () => {
    for (const def of CASES) {
      expect(ALL_CASES.some((k) => k.id === def.id && k.recognition === def.recognition)).toBe(true);
    }
  });

  test("scrambles parse and reference existing cases", async () => {
    const ids = new Set(ALL_CASES.map((k) => k.id));
    for (const [id, list] of Object.entries(CASE_SCRAMBLES)) {
      expect(ids.has(id), id).toBe(true);
      const def = ALL_CASES.find((k) => k.id === id)!;
      const kpuzzle = await kpuzzleFor(def.puzzle);
      for (const s of list) {
        kpuzzle.algToTransformation(new Alg(s));
      }
    }
  });
});
