/**
 * Machine-verification of every published algorithm on the cubing.js kpuzzle.
 * Every 3x3 alg must satisfy its stickering's REAL invariant (an inverse
 * round-trip is true of any alg, so it gates nothing):
 *  - OLL/OCLL: forward-applied to solved (rotation-normalized), every piece
 *    outside the U layer stays solved — the alg preserves F2L;
 *  - PLL: preserves F2L AND leaves every U-layer edge/corner in solved
 *    orientation — a pure permutation;
 *  - F2L: touches only the U layer + the FR slot (slot detected mechanically
 *    in scripts/lib/kpuzzle-utils.mjs, shared with scripts/verify-f2l.mjs).
 * One verified scramble per 3x3 case must be solved by the primary alg.
 * 4x4/5x5 algs are parse+legality checked here — their deep checks live in
 * scripts/verify-f2l.mjs / verify-l2e.mjs (npm run verify:data).
 *
 * The same discipline covers the player's stickering masks: the generated
 * table in src/lib/stickering.ts is re-derived from cubing.js here, and every
 * case's emitted mask must highlight exactly the pieces its algorithm fixes.
 */
import { describe, expect, test } from "vitest";
import { Alg } from "cubing/alg";
import { puzzles } from "cubing/puzzles";
import type { KPuzzle } from "cubing/kpuzzle";

import { ALL_CASES, CASES, caseById, primaryAlg, type CaseDef } from "../src/data/algs";
import { CASE_SCRAMBLES } from "../src/data/fullsets.gen";
import { RICH } from "../src/data/fullsets.rich.gen";
import { BASE_MASKS, FRAME, SETUP_ALG, maskFor } from "../src/lib/stickering";
import { groupSize } from "../src/lib/trainer";
import { makeSlotKit, type SlotKit } from "../scripts/lib/kpuzzle-utils.mjs";

const kpuzzleCache = new Map<string, Promise<KPuzzle>>();

function kpuzzleFor(puzzle: string): Promise<KPuzzle> {
  let p = kpuzzleCache.get(puzzle);
  if (!p) {
    p = puzzles[puzzle]!.kpuzzle();
    kpuzzleCache.set(puzzle, p);
  }
  return p;
}

let slotKit: Promise<SlotKit> | undefined;

function kit3(): Promise<SlotKit> {
  slotKit ??= kpuzzleFor("3x3x3").then((kp) => makeSlotKit(kp));
  return slotKit;
}

/** Assert the stickering's invariant on the forward-applied, rotation-normalized state. */
async function checkStickeringInvariant(def: CaseDef, moves: string): Promise<void> {
  const kit = await kit3();
  const t = kit.rightRotNormalize(kit.toT(moves)); // toT throws on illegal moves
  const pattern = kit.solved.applyTransformation(t);
  switch (def.stickering) {
    case "OLL":
    case "OCLL":
      expect(kit.outsideSolved(pattern, { allowFRSlot: false }), "preserves F2L").toBe(true);
      break;
    case "PLL":
      expect(kit.outsideSolved(pattern, { allowFRSlot: false }), "preserves F2L").toBe(true);
      expect(kit.uLayerOriented(pattern), "pure U-layer permutation").toBe(true);
      break;
    case "F2L":
      expect(
        kit.outsideSolved(pattern, { allowFRSlot: true }),
        "touches only U layer + FR slot",
      ).toBe(true);
      break;
    default:
      throw new Error(`no invariant for 3x3 stickering "${def.stickering}" (${def.id})`);
  }
}

describe("every 3x3 algorithm satisfies its stickering's invariant", () => {
  for (const def of ALL_CASES.filter((k) => k.puzzle === "3x3x3")) {
    for (const [i, variant] of def.algs.entries()) {
      test(`${def.id} [${def.stickering}] alg[${i}] (${variant.moves})`, async () => {
        await checkStickeringInvariant(def, variant.moves);
      });
    }
  }
});

describe("every big-cube algorithm parses and is legal on its puzzle", () => {
  for (const def of ALL_CASES.filter((k) => k.puzzle !== "3x3x3")) {
    for (const [i, variant] of def.algs.entries()) {
      test(`${def.id} alg[${i}] (${variant.moves})`, async () => {
        const kpuzzle = await kpuzzleFor(def.puzzle);
        kpuzzle.algToTransformation(new Alg(variant.moves)); // throws on unknown moves
      });
    }
  }
});

describe("every rich alternate algorithm passes the same gate as its case", () => {
  for (const [id, rich] of Object.entries(RICH)) {
    const def = caseById.get(id);
    for (const [i, variant] of rich.alternates.entries()) {
      test(`${id} alt[${i}] (${variant.moves})`, async () => {
        expect(def, `RICH id ${id} missing from ALL_CASES`).toBeTruthy();
        if (def!.puzzle === "3x3x3") {
          await checkStickeringInvariant(def!, variant.moves);
        } else {
          (await kpuzzleFor(def!.puzzle)).algToTransformation(new Alg(variant.moves));
        }
      });
    }
  }
});

describe("one verified scramble per 3x3 case is solved by its primary alg", () => {
  for (const [id, scrambles] of Object.entries(CASE_SCRAMBLES)) {
    const def = caseById.get(id);
    if (!def || def.puzzle !== "3x3x3" || scrambles.length === 0) continue;
    test(`${id} scramble[0] + primary alg completes F2L`, async () => {
      const kit = await kit3();
      const sT = kit.toT(scrambles[0]!);
      const aT = kit.toT(primaryAlg(def));
      // A case is an AUF-equivalence class: a scramble may set it up a U turn
      // away from the alg's execution angle, so enumerate the pre-AUF. Final
      // U turns need no enumeration — they cannot move non-U-layer pieces,
      // which is all this asserts (last-layer completion is each stickering's
      // own gate above).
      const ok = kit.AUF_T.some((u) =>
        kit.outsideSolved(
          kit.solved.applyTransformation(
            kit.rightRotNormalize(sT.applyTransformation(u).applyTransformation(aT)),
          ),
          { allowFRSlot: false },
        ),
      );
      expect(ok, "scramble + (pre-AUF) + primary alg leaves F2L solved").toBe(true);
    });
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
      expect(ALL_CASES.some((k) => k.id === def.id && k.recognition === def.recognition)).toBe(
        true,
      );
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

/** Piece-mask chars that still carry the sticker's real colour. */
const LIT = new Set(["-", "O", "P"]);

/**
 * `parseSerializedStickeringMask`'s char map, inverted — the spec the
 * generator is pinned against. Read out of cubing.js's own bundle
 * (chunk-VRTKWZPL.js `pieceStickerings` + `charMap`).
 */
const CHAR_BY_FACELETS: Record<string, string> = {
  "regular,regular,regular,regular,regular": "-",
  "dim,dim,dim,dim,dim": "D",
  "ignored,ignored,ignored,ignored,ignored": "I",
  "invisible,invisible,invisible,invisible,invisible": "X",
  "regular,ignored,ignored,ignored,ignored": "O",
  "dim,regular,regular,regular,regular": "P",
  "dim,ignored,ignored,ignored,ignored": "o",
  "oriented,ignored,ignored,ignored,ignored": "?",
  "mystery,mystery,mystery,mystery,mystery": "M",
};

const orbitChars = (mask: string): Record<string, string> =>
  Object.fromEntries(mask.split(",").map((segment) => segment.split(":") as [string, string]));

describe("stickering masks", () => {
  /**
   * cubing.js hard-codes the cube palette per axis in Cube3D (`axesInfo`, face
   * order U L F R B D) and exposes no colour-scheme API, so SETUP_ALG is the
   * only thing between the player and a white-on-top cube. CENTERS piece order
   * is U L F R B D, so centre cubie i wears the colour of face i.
   */
  const CUBING_PALETTE = ["white", "orange", "green", "red", "blue", "yellow"];
  /** CLAUDE.md § Rubik's Cube Color Scheme, in the same U L F R B D order. */
  const CUBEPATH_SCHEME = ["yellow", "blue", "red", "green", "orange", "white"];

  test("the setup rotation paints the Cubepath colour scheme", async () => {
    const kpuzzle = await kpuzzleFor("3x3x3");
    const centers = kpuzzle.defaultPattern().applyAlg(SETUP_ALG).patternData.CENTERS!.pieces;
    expect(centers.map((cubie) => CUBING_PALETTE[cubie])).toEqual(CUBEPATH_SCHEME);
  });

  test("the generated FRAME is the setup rotation's permutation", async () => {
    const kpuzzle = await kpuzzleFor("3x3x3");
    const setup = kpuzzle.defaultPattern().applyAlg(SETUP_ALG);
    for (const { orbitName } of kpuzzle.definition.orbits) {
      expect([...FRAME[orbitName]!], orbitName).toEqual([...setup.patternData[orbitName]!.pieces]);
    }
  });

  test("the generated BASE_MASKS still match cubing.js", async () => {
    const { cube3x3x3 } = await import("cubing/puzzles");
    const kpuzzle = await kpuzzleFor("3x3x3");
    for (const name of Object.keys(BASE_MASKS)) {
      const mask = await cube3x3x3.stickeringMask!(name);
      const expected = kpuzzle.definition.orbits
        .map(({ orbitName, numPieces }) => {
          const pieces = mask.orbits[orbitName]!.pieces;
          const chars = Array.from({ length: numPieces }, (_, i) => {
            const key = pieces[i]!.facelets.map((f) => (typeof f === "string" ? f : f!.mask)).join(
              ",",
            );
            return CHAR_BY_FACELETS[key] ?? `?${key}?`;
          }).join("");
          return `${orbitName}:${chars}`;
        })
        .join(",");
      expect(BASE_MASKS[name as keyof typeof BASE_MASKS], name).toBe(expected);
    }
  });

  test("big-cube and full-cube cases get no mask", async () => {
    for (const def of ALL_CASES) {
      const mask = await maskFor(def.puzzle, def.stickering, primaryAlg(def));
      if (def.puzzle !== "3x3x3" || def.stickering === "full") {
        expect(mask, def.id).toBeUndefined();
      } else {
        expect(mask, def.id).toBeTruthy();
      }
    }
  });
});

describe("every mask highlights exactly the pieces its algorithm fixes", () => {
  const masked = ALL_CASES.filter((k) => k.puzzle === "3x3x3" && k.stickering !== "full");
  for (const def of masked) {
    test(`${def.id} [${def.stickering}]`, async () => {
      const kit = await kit3();
      const alg = primaryAlg(def);
      const mask = (await maskFor(def.puzzle, def.stickering, alg))!;
      const chars = orbitChars(mask);
      const base = orbitChars(BASE_MASKS[def.stickering]);
      // What the player actually shows first: the case state, re-oriented so
      // the centres are home (an alg written with a whole-cube rotation would
      // otherwise look like it disturbs every piece).
      const state = kit.normalizePattern(kit.solved.applyTransformation(kit.toT(alg).invert()));
      // Derived here, not read from FRAME: the remap is half of what's on test.
      const setup = kit.solved.applyAlg(SETUP_ALG);

      for (const orbitName of ["EDGES", "CORNERS"]) {
        const emitted = chars[orbitName]!;
        const frame = setup.patternData[orbitName]!.pieces;
        const now = state.patternData[orbitName]!;
        const home = kit.solved.patternData[orbitName]!;
        expect(emitted.length, `${orbitName} length`).toBe(frame.length);
        for (let slot = 0; slot < frame.length; slot++) {
          // A mask entry binds to the CUBIE, so read the char at the index of
          // the cubie the setup rotation parks in this slot.
          const char = emitted[frame[slot]!]!;
          expect(Object.values(CHAR_BY_FACELETS), `${orbitName}[${slot}] char`).toContain(char);
          const solved =
            now.pieces[slot] === home.pieces[slot] &&
            now.orientation[slot] === home.orientation[slot];
          if (LIT.has(char)) {
            expect(solved, `${orbitName}[${slot}] highlighted but already solved`).toBe(false);
          }
          if (LIT.has(base[orbitName]![slot]!) && !solved) {
            expect(LIT.has(char), `${orbitName}[${slot}] fixed by the alg but dimmed`).toBe(true);
          }
        }
      }
    });
  }
});
