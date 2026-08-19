/**
 * Machine-verification of every published algorithm on the cubing.js kpuzzle.
 * A case's primary algorithm must solve the state its own inverse creates.
 * This is the CI gate that makes a wrong algorithm a build failure.
 */
import { describe, expect, test } from "vitest";
import { Alg } from "cubing/alg";
import { puzzles } from "cubing/puzzles";
import type { KPuzzle } from "cubing/kpuzzle";

import { CASES, primaryAlg } from "../src/data/algs";

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
  for (const def of CASES) {
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

describe("dataset invariants", () => {
  test("ids are unique", () => {
    const ids = CASES.map((k) => k.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  test("every case has exactly one primary algorithm", () => {
    for (const def of CASES) {
      expect(def.algs.filter((a) => a.primary).length, def.id).toBe(1);
      expect(primaryAlg(def)).toBeTruthy();
    }
  });

  test("prereqs reference existing cases", () => {
    const ids = new Set(CASES.map((k) => k.id));
    for (const def of CASES) {
      for (const p of def.prereqs ?? []) {
        expect(ids.has(p), `${def.id} prereq ${p}`).toBe(true);
      }
    }
  });
});
