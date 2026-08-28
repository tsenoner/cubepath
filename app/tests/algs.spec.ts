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
import { readFileSync, readdirSync } from "node:fs";

import { describe, expect, test } from "vitest";
import { Alg } from "cubing/alg";
import { puzzles } from "cubing/puzzles";
import type { KPuzzle } from "cubing/kpuzzle";

import {
  ALL_CASES,
  CASES,
  caseById,
  primaryAlg,
  type CaseDef,
  type Puzzle,
} from "../src/data/algs";
import { CASE_SCRAMBLES } from "../src/data/fullsets.gen";
import { RICH } from "../src/data/fullsets.rich.gen";
import {
  BASE_MASKS,
  FRAMES,
  QUIET,
  SETUP_ALG,
  contextForPlayer,
  hasHomeOrientation,
  maskFor,
} from "../src/lib/stickering";
import {
  BIG_CUBE_GREY,
  BIG_CUBE_PALETTE,
  LADDERS,
  LADDER_PUZZLE,
  LOW_CONTRAST_PAIRS,
  ORBIT_KINDS,
  PIECE_NAMES,
  PLAYER_GREY,
  PLAYER_PALETTE,
  RENDERED_LADDERS,
  STAGES,
  TIER_CHARS,
  contextForCase,
  contrastRatio,
  positionOf,
  priorStages,
  stageMask,
  stagePieces,
  type LadderKey,
  type StageKey,
  type TierPair,
} from "../src/lib/ladders";
import { experimental_AstroContainer as AstroContainer } from "astro/container";
import CaseRow from "../src/components/CaseRow.astro";
import TwistyPlayer from "../src/components/TwistyPlayer.astro";
import STAGES_JSON from "../src/data/extracted/stages.json";
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

/**
 * The case state an algorithm puts the player in, in the STANDARD frame.
 *
 * `normalizePattern` is the WRONG normalizer for this and every one of these
 * assertions used it. A case state is a PRE-state — `solved · alg⁻¹` — so any
 * net whole-cube rotation the algorithm carries sits on the LEFT, and
 * kpuzzle-utils says so in as many words ("Using the wrong side conjugates the
 * state onto the wrong faces"). Right-composing instead still brings the
 * centres home, so the search succeeds and nothing looks wrong; it just answers
 * about a different cube. `stickering.ts` had the same error, and because the
 * test shared it, all 35 cases whose primary algorithm carries a rotation —
 * 28 F2L, the five rotating PLLs (Aa, Ab, E, Ja, V), two 5x5 L2E — passed while
 * highlighting the wrong pieces. Left-compose, and never reach for
 * `normalizePattern` on a state built from an inverse.
 */
function caseStateOf(kit: SlotKit, alg: string) {
  return kit.solved.applyTransformation(kit.leftRotNormalize(kit.toT(alg).invert()));
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

  test("no big-cube case ships a trainer scramble", () => {
    // The extraction ships scrambles for all 49 generated 4x4 cases, and every
    // one of them is outer-layer moves only. Outer turns carry both wings of an
    // edge together, so from a reduced cube they cannot produce either parity:
    // all 196 set up an ordinary 3x3-legal state rather than the case they
    // name, and a learner drilling 4x4 parity never met the case. The gate that
    // should have caught it — "one verified scramble per 3x3 case" above —
    // skips anything that is not 3x3x3, which is exactly how it survived.
    //
    // gen-cases.mjs now drops them and `setupScramble` falls back to
    // inverse-of-alg, which is correct for any puzzle. If big-cube scrambles
    // are ever reinstated they must be verified to produce their case first,
    // and this assertion is what forces that conversation.
    const bigCube = Object.keys(CASE_SCRAMBLES).filter((id) => {
      const def = ALL_CASES.find((k) => k.id === id);
      return def !== undefined && def.puzzle !== "3x3x3";
    });
    expect(bigCube, "big-cube scrambles are unverified — see the comment").toEqual([]);
  });

  test("every shipped scramble belongs to a case the 3x3 gate actually checks", () => {
    // Pairs with the test above: together they say every scramble in the file
    // is covered by the "solved by its primary alg" describe block, so no
    // scramble can ship unverified by being a puzzle that block skips.
    for (const id of Object.keys(CASE_SCRAMBLES)) {
      const def = ALL_CASES.find((k) => k.id === id);
      expect(def?.puzzle, id).toBe("3x3x3");
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

  test("every puzzle in the Puzzle union has a frame — none silently loses its mask", () => {
    // The failure this replaces: `build()` returned undefined for anything but
    // 3x3, so all 63 4x4/5x5 cases rendered with the attribute literally null
    // and one tier. Widening the union without regenerating now fails here.
    for (const puzzle of new Set(ALL_CASES.map((k) => k.puzzle))) {
      expect(FRAMES[puzzle], `${puzzle} has no ${SETUP_ALG} frame`).toBeTruthy();
      expect(ORBIT_KINDS[puzzle], `${puzzle} has no orbit kinds`).toBeTruthy();
    }
  });

  test("every generated FRAME is the setup rotation's own permutation", async () => {
    for (const puzzle of Object.keys(FRAMES) as Puzzle[]) {
      const kpuzzle = await kpuzzleFor(puzzle);
      // Read off the transformation, not off a pattern: big cubes label
      // interchangeable centres by face colour, so a pattern's `pieces` array
      // is not a permutation there.
      const setup = kpuzzle.algToTransformation(SETUP_ALG);
      for (const { orbitName, numPieces } of kpuzzle.definition.orbits) {
        const perm = [...setup.transformationData[orbitName]!.permutation];
        expect([...FRAMES[puzzle]![orbitName]!], `${puzzle}/${orbitName}`).toEqual(perm);
        expect(new Set(perm).size, `${puzzle}/${orbitName} is a permutation`).toBe(numPieces);
      }
    }
  });

  test("orbit kinds are how many faces move the orbit — 3 corner, 2 edge, 1 centre", async () => {
    const faces = ["U", "D", "F", "B", "R", "L"];
    for (const puzzle of Object.keys(ORBIT_KINDS) as Puzzle[]) {
      const kpuzzle = await kpuzzleFor(puzzle);
      for (const { orbitName, numPieces } of kpuzzle.definition.orbits) {
        const counts = new Set(
          Array.from(
            { length: numPieces },
            (_, slot) =>
              faces.filter((f) => {
                const d = kpuzzle.algToTransformation(f).transformationData[orbitName]!;
                return d.permutation[slot] !== slot || d.orientationDelta[slot] !== 0;
              }).length,
          ),
        );
        expect(counts.size, `${puzzle}/${orbitName} face counts`).toBe(1);
        const kind = { 1: "center", 2: "edge", 3: "corner" }[[...counts][0]!];
        expect(ORBIT_KINDS[puzzle]![orbitName], `${puzzle}/${orbitName}`).toBe(kind);
      }
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

  test("without a ladder context, `full` and big cubes still mean 'show everything'", async () => {
    // Unchanged fallback: a caller that names no step gets cubing.js's two
    // tiers, and `full` gets no mask at all. What changed is that no case ships
    // through this path any more — see the rendered-attribute suite below.
    for (const def of ALL_CASES) {
      const mask = await maskFor(def.puzzle, def.stickering, primaryAlg(def));
      if (def.puzzle !== "3x3x3" || def.stickering === "full") {
        expect(mask, def.id).toBeUndefined();
      } else {
        expect(mask, def.id).toBeTruthy();
      }
    }
  });

  test("with a ladder context, every case gets a mask — 4x4 and 5x5 included", async () => {
    for (const def of ALL_CASES) {
      const mask = await maskFor(def.puzzle, def.stickering, primaryAlg(def), contextForCase(def));
      expect(mask, `${def.id} (${def.puzzle}) gets a ladder mask`).toBeTruthy();
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
      const state = caseStateOf(kit, alg);
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

// ─────────────────────────────────────────────────────────────────────────────
// The progressive stage ladder (src/lib/ladders.ts + src/data/extracted/stages.json)
// ─────────────────────────────────────────────────────────────────────────────

/** Chars that mean "solved by an earlier stage — preserve it". */
const DIMMED = new Set(["D", "o"]);
/** The single char that means "the method has not reached this piece". */
const GREY = "I";

const orbitCharsOf = (mask: string): Record<string, string> => orbitChars(mask);

describe("the stage ladder", () => {
  test("TIER_CHARS' dim row IS the QUIET demotion that already ships", () => {
    for (const aspect of ["both", "orientation", "permutation"] as const) {
      expect(TIER_CHARS.dim[aspect], aspect).toBe(QUIET[TIER_CHARS.highlight[aspect]!]);
      expect(TIER_CHARS.grey[aspect], aspect).toBe(GREY);
    }
  });

  test("the generated slot names are the faces that move each piece", async () => {
    for (const puzzle of Object.keys(PIECE_NAMES) as Puzzle[]) await namesMatch(puzzle);
  });

  async function namesMatch(puzzle: Puzzle) {
    const kpuzzle = await kpuzzleFor(puzzle);
    const faces = ["U", "D", "F", "B", "R", "L"];
    const movedBy = (move: string): Record<string, boolean[]> => {
      const t = kpuzzle.algToTransformation(move);
      return Object.fromEntries(
        kpuzzle.definition.orbits.map(({ orbitName }) => {
          const d = t.transformationData[orbitName]!;
          return [orbitName, d.permutation.map((p, i) => p !== i || d.orientationDelta[i] !== 0)];
        }),
      );
    };
    const byFace = Object.fromEntries(faces.map((f) => [f, movedBy(f)]));
    for (const { orbitName, numPieces } of kpuzzle.definition.orbits) {
      const expected = Array.from({ length: numPieces }, (_, slot) =>
        faces.filter((f) => byFace[f]![orbitName]![slot]).join(""),
      );
      expect([...PIECE_NAMES[puzzle]![orbitName]!], `${puzzle}/${orbitName}`).toEqual(expected);
    }
  }

  test("every ladder stage a case can reach is on a ladder", () => {
    for (const def of ALL_CASES) {
      const ctx = contextForCase(def);
      expect(LADDERS[ctx.ladder], `${def.id} ladder ${ctx.ladder}`).toBeTruthy();
      expect(() => positionOf(ctx.stage, ctx.ladder), `${def.id} ${ctx.stage}`).not.toThrow();
    }
  });

  test("every phase that ships has an explicit ladder — none falls through to the default", () => {
    // A new phase value must be a decision, not a silent default. `phase` is an
    // opaque tag, not a key into PHASES, so this is the only gate on it.
    const explicit = new Set(Object.keys(STAGES_JSON.ladderOfPhase));
    for (const phase of new Set(ALL_CASES.map((k) => k.phase))) {
      expect(explicit.has(phase), `phase "${phase}" has no ladder entry`).toBe(true);
    }
  });

  for (const ladder of RENDERED_LADDERS) {
    const puzzle = LADDER_PUZZLE[ladder];
    const kinds = ORBIT_KINDS[puzzle]!;
    const isCentre = (orbitName: string) => kinds[orbitName] === "center";

    describe(`ladder "${ladder}" (${puzzle})`, () => {
      test("is a chain: its stages cover every piece of the puzzle", async () => {
        const kpuzzle = await kpuzzleFor(puzzle as Puzzle);
        const seen: Record<string, Set<number>> = {};
        for (const stage of LADDERS[ladder]) {
          const pieces = stagePieces(stage, puzzle);
          expect(pieces, `${stage} has no ${puzzle} piece set`).toBeTruthy();
          for (const [orbitName, list] of Object.entries(pieces!)) {
            seen[orbitName] ??= new Set();
            for (const i of list) seen[orbitName]!.add(i);
          }
        }
        for (const { orbitName, numPieces } of kpuzzle.definition.orbits) {
          expect(seen[orbitName]!.size, `${puzzle}/${orbitName}`).toBe(numPieces);
        }
      });

      for (const stage of Object.keys(STAGES).filter((s) => {
        try {
          positionOf(s as StageKey, ladder);
          return stagePieces(s as StageKey, puzzle) != null;
        } catch {
          return false;
        }
      }) as StageKey[]) {
        test(`stage "${stage}": highlight = itself, dim = every earlier stage, grey = the rest`, () => {
          const ctx = { ladder, stage };
          const mask = stageMask(ctx)!;
          expect(mask, "stage carries a mask").toBeTruthy();
          const chars = orbitCharsOf(mask);
          const own = stagePieces(stage, puzzle)!;
          const aspect = STAGES[stage].aspect;

          // DIM should be exactly the union of the earlier stages' piece sets,
          // minus anything this stage highlights.
          const priorUnion: Record<string, Set<number>> = {};
          for (const p of priorStages(ctx)) {
            for (const [orbitName, list] of Object.entries(stagePieces(p, puzzle)!)) {
              priorUnion[orbitName] ??= new Set();
              for (const i of list) priorUnion[orbitName]!.add(i);
            }
          }
          // Centres are owned by ONE stage per ladder — the first that claims
          // them — and dim at every other. Derived here from the ladder rather
          // than read back from the file, so it is an independent check.
          const centreOwner = LADDERS[ladder].find((k) =>
            Object.entries(stagePieces(k, puzzle) ?? {}).some(
              ([orbitName, list]) => isCentre(orbitName) && list.length > 0,
            ),
          );

          for (const [orbitName, segment] of Object.entries(chars)) {
            const centre = isCentre(orbitName);
            const highlighted = new Set(
              centre && stage !== centreOwner ? [] : (own[orbitName] ?? []),
            );
            for (let slot = 0; slot < segment.length; slot++) {
              const char = segment[slot]!;
              const isHi = LIT.has(char);
              const isDim = DIMMED.has(char);
              const isGrey = char === GREY;
              expect(isHi || isDim || isGrey, `${orbitName}[${slot}] char "${char}"`).toBe(true);
              // No piece is both highlighted and dimmed — the chars are
              // disjoint sets, so this is the assertion that they never mix.
              expect([isHi, isDim, isGrey].filter(Boolean).length).toBe(1);

              if (highlighted.has(slot)) {
                expect(char, `${orbitName}[${slot}] is this stage's own piece`).toBe(
                  TIER_CHARS.highlight[aspect],
                );
              } else if (centre) {
                expect(isDim, `${orbitName}[${slot}] is a centre, never grey`).toBe(true);
              } else if (priorUnion[orbitName]?.has(slot)) {
                expect(isDim, `${orbitName}[${slot}] solved earlier, must be dim`).toBe(true);
              } else {
                expect(isGrey, `${orbitName}[${slot}] not yet reached, must be grey`).toBe(true);
              }
            }
          }
        });

        test(`stage "${stage}": centres are never grey`, () => {
          const chars = orbitCharsOf(stageMask({ ladder, stage })!);
          for (const [orbitName, segment] of Object.entries(chars)) {
            if (!isCentre(orbitName)) continue;
            expect(segment.includes(GREY), `${orbitName} is the recognition frame`).toBe(false);
          }
        });
      }
    });
  }

  /**
   * GOLDEN MASKS — every stage's un-narrowed mask exactly as the player
   * receives it (post-FRAME). Checked in because it is the artifact a reviewer
   * can actually read: change the ladder and this table changes visibly.
   *
   * Read them as: `-`/`O`/`P` highlight, `D`/`o` dim, `I` grey. EDGES slots are
   * U(4) D(4) E-slice(4); CORNERS U(4) D(4); CENTERS U L F R B D.
   */
  const GOLDEN: Record<string, Record<string, string>> = {
    "beginner": {
      "cross": "EDGES:----IIIIIIII,CORNERS:IIIIIIII,CENTERS:------",
      "f1l": "EDGES:DDDDIIIIIIII,CORNERS:----IIII,CENTERS:DDDDDD",
      "e-layer": "EDGES:DDDDIIII----,CORNERS:DDDDIIII,CENTERS:DDDDDD",
      "eo": "EDGES:DDDDOOOODDDD,CORNERS:DDDDIIII,CENTERS:DDDDDD",
      "oc": "EDGES:DDDDDDDDDDDD,CORNERS:DDDDOOOO,CENTERS:DDDDDD",
      "cp": "EDGES:DDDDDDDDDDDD,CORNERS:DDDDPPPP,CENTERS:DDDDDD",
      "ep": "EDGES:DDDDPPPPDDDD,CORNERS:DDDDIIII,CENTERS:DDDDDD",
      "f2l": "EDGES:DDDDIIII----,CORNERS:----IIII,CENTERS:DDDDDD",
      "oll": "EDGES:DDDDOOOODDDD,CORNERS:DDDDOOOO,CENTERS:DDDDDD",
      "pll": "EDGES:DDDDPPPPDDDD,CORNERS:DDDDPPPP,CENTERS:DDDDDD",
    },
    "cfop": {
      "cross": "EDGES:----IIIIIIII,CORNERS:IIIIIIII,CENTERS:------",
      "f1l": "EDGES:DDDDIIIIIIII,CORNERS:----IIII,CENTERS:DDDDDD",
      "e-layer": "EDGES:DDDDIIII----,CORNERS:DDDDIIII,CENTERS:DDDDDD",
      "eo": "EDGES:DDDDOOOODDDD,CORNERS:DDDDIIII,CENTERS:DDDDDD",
      "oc": "EDGES:DDDDooooDDDD,CORNERS:DDDDOOOO,CENTERS:DDDDDD",
      "cp": "EDGES:DDDDooooDDDD,CORNERS:DDDDPPPP,CENTERS:DDDDDD",
      "ep": "EDGES:DDDDPPPPDDDD,CORNERS:DDDDDDDD,CENTERS:DDDDDD",
      "f2l": "EDGES:DDDDIIII----,CORNERS:----IIII,CENTERS:DDDDDD",
      "oll": "EDGES:DDDDOOOODDDD,CORNERS:DDDDOOOO,CENTERS:DDDDDD",
      "pll": "EDGES:DDDDPPPPDDDD,CORNERS:DDDDPPPP,CENTERS:DDDDDD",
    },
    // The big-cube ladders, which used to carry ordering and no masks at all.
    // EDGES here is the 24 wings; the reduction stages own whole orbits, and
    // every 3x3 stage after them re-highlights the subset it settles.
    "444": {
      "444-centers":
        "CORNERS:IIIIIIII,EDGES:IIIIIIIIIIIIIIIIIIIIIIII,CENTERS:------------------------",
      "444-pairing":
        "CORNERS:IIIIIIII,EDGES:------------------------,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
      "cross": "CORNERS:IIIIIIII,EDGES:-----DDD-DDD-DDD-DDDDDDD,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
      "f1l": "CORNERS:----IIII,EDGES:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
      "e-layer": "CORNERS:DDDDIIII,EDGES:DDDDD-D-D-D-D-D-D-D-DDDD,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
      "eo": "CORNERS:DDDDIIII,EDGES:DDDDDDODDDODDDODDDODOOOO,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
      "oc": "CORNERS:DDDDOOOO,EDGES:DDDDDDoDDDoDDDoDDDoDoooo,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
      "cp": "CORNERS:DDDDPPPP,EDGES:DDDDDDoDDDoDDDoDDDoDoooo,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
      "ep": "CORNERS:DDDDDDDD,EDGES:DDDDDDPDDDPDDDPDDDPDPPPP,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
      "f2l": "CORNERS:----IIII,EDGES:DDDDD-D-D-D-D-D-D-D-DDDD,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
      "oll": "CORNERS:DDDDOOOO,EDGES:DDDDDDODDDODDDODDDODOOOO,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
      "pll": "CORNERS:DDDDPPPP,EDGES:DDDDDDPDDDPDDDPDDDPDPPPP,CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
    },
    "555": {
      "555-centers":
        "EDGES:IIIIIIIIIIIIIIIIIIIIIIII,EDGES2:IIIIIIIIIIII,CORNERS:IIIIIIII," +
        "CENTERS:------------------------,CENTERS2:------------------------,CENTERS3:------",
      "555-pairing":
        "EDGES:------------------------,EDGES2:------------,CORNERS:IIIIIIII," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
      "cross":
        "EDGES:-----DDD-DDD-DDD-DDDDDDD,EDGES2:DDDDDD-D--D-,CORNERS:IIIIIIII," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
      "f1l":
        "EDGES:DDDDDDDDDDDDDDDDDDDDDDDD,EDGES2:DDDDDDDDDDDD,CORNERS:----IIII," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
      "e-layer":
        "EDGES:DDDDD-D-D-D-D-D-D-D-DDDD,EDGES2:D-DD-DD-DD-D,CORNERS:DDDDIIII," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
      "eo":
        "EDGES:DDDDDDODDDODDDODDDODOOOO,EDGES2:ODOODODDDDDD,CORNERS:DDDDIIII," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
      "oc":
        "EDGES:DDDDDDoDDDoDDDoDDDoDoooo,EDGES2:oDooDoDDDDDD,CORNERS:DDDDOOOO," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
      "cp":
        "EDGES:DDDDDDoDDDoDDDoDDDoDoooo,EDGES2:oDooDoDDDDDD,CORNERS:DDDDPPPP," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
      "ep":
        "EDGES:DDDDDDPDDDPDDDPDDDPDPPPP,EDGES2:PDPPDPDDDDDD,CORNERS:DDDDDDDD," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
      "f2l":
        "EDGES:DDDDD-D-D-D-D-D-D-D-DDDD,EDGES2:D-DD-DD-DD-D,CORNERS:----IIII," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
      "oll":
        "EDGES:DDDDDDODDDODDDODDDODOOOO,EDGES2:ODOODODDDDDD,CORNERS:DDDDOOOO," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
      "pll":
        "EDGES:DDDDDDPDDDPDDDPDDDPDPPPP,EDGES2:PDPPDPDDDDDD,CORNERS:DDDDPPPP," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
    },
  };

  test("the emitted stage masks match the checked-in golden table", async () => {
    for (const [ladder, table] of Object.entries(GOLDEN)) {
      // Derived here, not read from FRAMES: the slot -> cubie remap is half of
      // what the golden table asserts.
      const kpuzzle = await kpuzzleFor(LADDER_PUZZLE[ladder as LadderKey] as Puzzle);
      const setup = kpuzzle.algToTransformation(SETUP_ALG);
      const frameOf = (orbitName: string) => setup.transformationData[orbitName]!.permutation;
      // Every stage the ladder emits has a golden row: a new stage cannot slip
      // in unreviewed, and a deleted one cannot leave a stale row behind.
      expect(Object.keys(table).sort(), `${ladder} golden rows`).toEqual(
        Object.keys(STAGES)
          .filter((k) => stageMask({ ladder: ladder as LadderKey, stage: k as StageKey }))
          .sort(),
      );
      for (const [stage, expected] of Object.entries(table)) {
        const emitted = stageMask({ ladder: ladder as LadderKey, stage: stage as StageKey })!
          .split(",")
          .map((segment) => {
            const [orbitName, chars] = segment.split(":") as [string, string];
            const frame = frameOf(orbitName);
            const out: string[] = new Array(chars.length);
            for (let slot = 0; slot < chars.length; slot++) out[frame[slot]!] = chars[slot]!;
            return `${orbitName}:${out.join("")}`;
          })
          .join(",");
        expect(emitted, `${ladder}/${stage}`).toBe(expected);
      }
    }
  });

  test("LAST-LAYER REGRESSION PIN: the derived masks are what ships today", () => {
    // Proof that the ladder is a no-op for the last layer: these come out
    // byte-identical to cubing.js's own OCLL and PLL scopes.
    expect(stageMask({ ladder: "cfop", stage: "oc" })).toBe(BASE_MASKS["OCLL"]);
    expect(stageMask({ ladder: "cfop", stage: "pll" })).toBe(BASE_MASKS["PLL"]);
    // OLL differs in exactly one char, deliberately: cubing.js leaves the U
    // centre regular, the ladder dims it. Centres are HIGHLIGHT at `cross` and
    // DIM thereafter, never re-highlighted and never grey.
    const derived = stageMask({ ladder: "cfop", stage: "oll" })!;
    const shipped = BASE_MASKS["OLL"];
    expect(derived.length).toBe(shipped.length);
    const diff = [...derived].flatMap((c, i) => (c === shipped[i] ? [] : [i]));
    expect(diff.length, "exactly one deliberate difference from cubing.js's OLL").toBe(1);
    expect(orbitCharsOf(derived)["CENTERS"]).toBe("DDDDDD");
    expect(orbitCharsOf(shipped)["CENTERS"]).toBe("-DDDDD");
  });

  test("the yellow-cross step stops claiming the last-layer corners", async () => {
    // The concrete bug the ladder fixes. eo.line declares stickering "OLL",
    // whose scope covers corners, so today it highlights four corners three
    // lessons before corner orientation is taught.
    const def = caseById.get("eo.line")!;
    const today = orbitCharsOf((await maskFor(def.puzzle, def.stickering, primaryAlg(def)))!);
    expect(today["CORNERS"]).toBe("DDDDOOOO");
    const withLadder = orbitCharsOf(
      (await maskFor(def.puzzle, def.stickering, primaryAlg(def), contextForCase(def)))!,
    );
    expect(withLadder["CORNERS"]).toBe("DDDDIIII");
  });
});

describe("algorithms that carry a net whole-cube rotation", () => {
  /**
   * A case state is a PRE-state (`solved · alg⁻¹`), so a rotation baked into
   * the algorithm sits on the LEFT of it. `stickering.ts` used to take it back
   * out on the RIGHT — and so did the four assertions above this one, via
   * `normalizePattern`, which is why nothing caught it. Both searches find a
   * rotation and both bring the centres home; they simply answer about
   * different cubes. The result was a mask that lit the wrong pieces on 35 of
   * the 185 cases, most visibly `pll.aa` — a pure three-cycle of U corners
   * that lit ONE corner, two of the three it should have lit having been
   * reported in the bottom layer.
   *
   * These are the cases whose primary algorithm has a net rotation. The list is
   * DERIVED, so an extraction that adds or drops one fails here rather than
   * quietly widening the blast radius of a regression. 27 cases carry one; 25
   * of them have a page (`444.pll.ka`/`kb` are locked), and all 25 shipped the
   * wrong mask.
   */
  const ROTATION_ALGS: string[] = [];
  for (const a of ["", "x", "x2", "x'", "z", "z'"])
    for (const b of ["", "y", "y2", "y'"]) ROTATION_ALGS.push([a, b].filter(Boolean).join(" "));

  test("27 of the 185 cases have one, and they are these", async () => {
    const found: string[] = [];
    for (const def of ALL_CASES) {
      const kp = await kpuzzleFor(def.puzzle);
      const state = kp
        .defaultPattern()
        .applyTransformation(kp.algToTransformation(primaryAlg(def)).invert());
      const centres = Object.entries(ORBIT_KINDS[def.puzzle]!)
        .filter(([, kind]) => kind === "center")
        .map(([orbitName]) => orbitName);
      const home = centres.every((o) =>
        state.patternData[o]!.pieces.every(
          (v, i) => v === kp.defaultPattern().patternData[o]!.pieces[i],
        ),
      );
      if (!home) found.push(def.id);
    }
    expect(found.length, found.join(" ")).toBe(27);
    expect(found.filter((id) => id.startsWith("pll.")).sort()).toEqual([
      "pll.aa",
      "pll.ab",
      "pll.e",
      "pll.ja",
      "pll.v",
    ]);
    expect(found.filter((id) => id.startsWith("f2l.")).length).toBe(18);
    expect(found.filter((id) => id.startsWith("444.")).sort()).toEqual([
      "444.pll.ka",
      "444.pll.kb",
    ]);
    expect(found.filter((id) => id.startsWith("555.")).sort()).toEqual(["555.l2e-12", "555.l2e-7"]);
  }, 60_000);

  /**
   * Spelled out on the ATTRIBUTE, because that is the only place the error was
   * ever visible. Left of the arrow is what the page shipped with the rotation
   * cancelled on the wrong side; right is the permutation each algorithm
   * really performs. `pll.v` is the one to keep: the broken mask lit the right
   * NUMBER of corners, on the wrong two slots — the shape of this bug that
   * survives being eyeballed.
   */
  const ROWS: [string, string, string][] = [
    ["pll.aa", "CORNERS:DDDDDDPD", "CORNERS:DDDDDPPP"],
    ["pll.ab", "CORNERS:DDDDDDDP", "CORNERS:DDDDPDPP"],
    ["pll.e", "CORNERS:DDDDPDDP", "CORNERS:DDDDPPPP"],
    ["pll.ja", "CORNERS:DDDDDPDD", "CORNERS:DDDDPPDD"],
    ["pll.v", "CORNERS:DDDDDPDP", "CORNERS:DDDDPDPD"],
    ["f2l.11", "CORNERS:D-DDIIII", "CORNERS:-DDDIIII"],
  ];

  for (const [id, wrong, right] of ROWS) {
    test(`${id} renders ${right}, not ${wrong}`, async () => {
      const chars = orbitChars((await renderedMask(CaseRow, { id }))!);
      const [orbitName, expected] = right.split(":") as [string, string];
      expect(chars[orbitName]).toBe(expected);
      expect(chars[orbitName]).not.toBe(wrong.split(":")[1]);
    });
  }

  test("all 41 F2L cases highlight the SAME slot, because they are all the FR slot", async () => {
    // 18 of them are written with a leading rotation. Under the wrong
    // normalization those 18 lit a different slot, so the set of rendered
    // masks split in two — which is what this asserts is gone.
    const seen = new Set<string>();
    for (const def of ALL_CASES.filter((d) => d.id.startsWith("f2l."))) {
      const chars = orbitChars((await renderedMask(CaseRow, { id: def.id }))!);
      const lit = [...chars["CORNERS"]!].map((c, i) => (LIT.has(c) ? i : -1)).filter((i) => i >= 0);
      if (lit.length) seen.add(lit.join(","));
    }
    expect([...seen]).toEqual(["0"]);
  }, 120_000);
});

describe("every ladder mask still highlights only pieces its algorithm fixes", () => {
  const masked = ALL_CASES.filter((k) => k.puzzle === "3x3x3");
  for (const def of masked) {
    test(`${def.id} [${contextForCase(def).ladder}/${contextForCase(def).stage}]`, async () => {
      const kit = await kit3();
      const alg = primaryAlg(def);
      const ctx = contextForCase(def);
      const mask = (await maskFor(def.puzzle, def.stickering, alg, ctx))!;
      expect(mask, `${def.id} gets a ladder mask`).toBeTruthy();
      const chars = orbitCharsOf(mask);
      const state = caseStateOf(kit, alg);
      const setup = kit.solved.applyAlg(SETUP_ALG);

      for (const orbitName of ["EDGES", "CORNERS"]) {
        const emitted = chars[orbitName]!;
        const frame = setup.patternData[orbitName]!.pieces;
        const now = state.patternData[orbitName]!;
        const home = kit.solved.patternData[orbitName]!;
        for (let slot = 0; slot < frame.length; slot++) {
          const char = emitted[frame[slot]!]!;
          const solved =
            now.pieces[slot] === home.pieces[slot] &&
            now.orientation[slot] === home.orientation[slot];
          if (LIT.has(char)) {
            expect(solved, `${orbitName}[${slot}] highlighted but already solved`).toBe(false);
          }
        }
      }
    });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// WHAT ACTUALLY REACHES THE PAGE
//
// This suite exists because of how the three-tier ladder shipped broken: every
// assertion above exercised `stageMask`/`maskFor` directly while
// TwistyPlayer.astro called `maskFor(puzzle, stickering, alg)` with no context
// at all. The functions were right, the tests were green, and 0 of 185 cases
// rendered a ladder mask. So these tests render the COMPONENT and read the
// `experimental-stickering-mask-orbits` attribute out of its HTML — the same
// string the browser gets. A missing attribute is `undefined` here, which is
// exactly the failure being guarded against.
// ─────────────────────────────────────────────────────────────────────────────

const MASK_ATTR = /experimental-stickering-mask-orbits="([^"]*)"/;

let containerPromise: ReturnType<typeof AstroContainer.create> | undefined;
const container = () => (containerPromise ??= AstroContainer.create());

/** The mask attribute a component actually renders, or undefined if it renders none. */
async function renderedMask(
  Component: Parameters<Awaited<ReturnType<typeof AstroContainer.create>>["renderToString"]>[0],
  props: Record<string, unknown>,
): Promise<string | undefined> {
  const html = await (await container()).renderToString(Component, { props });
  return MASK_ATTR.exec(html)?.[1];
}

describe("the rendered mask attribute", () => {
  /**
   * One row per tier-carrying shape the site renders, with the string spelled
   * out. Read them as: `-`/`O`/`P` highlight, `D`/`o` dim, `I` grey; 3x3 EDGES
   * slots are U(4) D(4) E-slice(4), CORNERS U(4) D(4), CENTERS U L F R B D.
   */
  const REPRESENTATIVE: [string, Record<string, unknown>, string][] = [
    [
      "cross — the four white edges lit, the rest of the cube not yet reached",
      { alg: "F R U R' U'", context: { ladder: "beginner", stage: "cross" } },
      "EDGES:D-DDIIIIIIII,CORNERS:IIIIIIII,CENTERS:------",
    ],
    [
      "f1l — white cross dim, the one corner this trigger moves in colour",
      { alg: "R U R' U'", anchor: "start", context: { ladder: "beginner", stage: "f1l" } },
      "EDGES:DDDDIIIIIIII,CORNERS:-DDDIIII,CENTERS:DDDDDD",
    ],
    [
      "e-layer — first layer dim, the middle edge lit, last layer grey",
      { alg: "U R U' R' U' F' U F", context: { ladder: "beginner", stage: "e-layer" } },
      "EDGES:DDDDIIII-DDD,CORNERS:DDDDIIII,CENTERS:DDDDDD",
    ],
    [
      "f2l — the pair (corner + edge) lit together, cross dim, last layer grey",
      {
        alg: "R U R' U'",
        stickering: "F2L",
        anchor: "start",
        context: { ladder: "cfop", stage: "f2l" },
      },
      "EDGES:DDDDIIII-DDD,CORNERS:-DDDIIII,CENTERS:DDDDDD",
    ],
    [
      "OLL — the misoriented pieces only, and the U centre dim rather than grey",
      { alg: "R U R' U R U2 R'", stickering: "OLL", context: { ladder: "cfop", stage: "oll" } },
      "EDGES:DDDDooooDDDD,CORNERS:DDDDOOOo,CENTERS:DDDDDD",
    ],
    [
      "PLL — the permuted edges only; orientation is an earlier step, so dim",
      { alg: "M2 U M U2 M' U M2", stickering: "PLL", context: { ladder: "cfop", stage: "pll" } },
      "EDGES:DDDDPPPDDDDD,CORNERS:DDDDDDDD,CENTERS:DDDDDD",
    ],
    [
      "4x4 centres — the reduction's first step: centres lit, nothing else reached",
      {
        alg: "Rw U Rw'",
        puzzle: "4x4x4",
        anchor: "start",
        context: { ladder: "444", stage: "444-centers" },
      },
      "CORNERS:IIIIIIII,EDGES:IIIIIIIIIIIIIIIIIIIIIIII,CENTERS:------------------------",
    ],
  ];

  for (const [label, props, expected] of REPRESENTATIVE) {
    test(`TwistyPlayer renders ${label}`, async () => {
      expect(await renderedMask(TwistyPlayer, props)).toBe(expected);
    });
  }

  /** The same, through the component the reference and the lessons actually use. */
  const ROWS: [string, string][] = [
    ["oll.27", "EDGES:DDDDooooDDDD,CORNERS:DDDDOOOo,CENTERS:DDDDDD"],
    ["oll.45", "EDGES:DDDDoOoODDDD,CORNERS:DDDDooOO,CENTERS:DDDDDD"],
    ["eo.line", "EDGES:DDDDoOoODDDD,CORNERS:DDDDIIII,CENTERS:DDDDDD"],
    ["pll.ua", "EDGES:DDDDPPPDDDDD,CORNERS:DDDDDDDD,CENTERS:DDDDDD"],
    ["f2l.1", "EDGES:DDDDIIII-DDD,CORNERS:-DDDIIII,CENTERS:DDDDDD"],
    [
      "444.oll-parity",
      "CORNERS:DDDDIIII,EDGES:DDDDDDoDDDoDDDODDDoDoOoo," + "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD",
    ],
    // The 5x5 row is the case the course TEACHES. It used to be 555.l2e-1,
    // which is now locked behind UNLOCKED["555-l2e-onelook"] — a mask assertion
    // is only worth having on a surface a learner can actually reach.
    [
      "555.l2e-6",
      "EDGES:DDDDDDDDDD-DDD-DDD-D---D,EDGES2:-DD-DDDDDDDD,CORNERS:IIIIIIII," +
        "CENTERS:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS2:DDDDDDDDDDDDDDDDDDDDDDDD,CENTERS3:DDDDDD",
    ],
  ];

  for (const [id, expected] of ROWS) {
    test(`CaseRow "${id}" renders its ladder mask`, async () => {
      expect(await renderedMask(CaseRow, { id })).toBe(expected);
    });
  }

  test("eo.line and oll.45 are the SAME algorithm and render DIFFERENT masks", async () => {
    // The whole reason the ladder cannot live on CaseDef. Both are
    // `F R U R' U' F'` with stickering "OLL"; the beginner lesson is orienting
    // edges (corners grey, three lessons away) and CFOP's OLL is doing both.
    const [line, oll] = await Promise.all([
      renderedMask(CaseRow, { id: "eo.line" }),
      renderedMask(CaseRow, { id: "oll.45" }),
    ]);
    expect(primaryAlg(caseById.get("eo.line")!)).toBe(primaryAlg(caseById.get("oll.45")!));
    expect(orbitChars(line!)["CORNERS"], "eo: the corners are not this step").toBe("DDDDIIII");
    expect(orbitChars(oll!)["CORNERS"], "oll: two corners are misoriented").toBe("DDDDooOO");
  });

  test("EVERY case renders a three-tier mask — none falls through to no attribute", async () => {
    for (const def of ALL_CASES) {
      const mask = await renderedMask(CaseRow, { id: def.id });
      expect(mask, `${def.id} (${def.puzzle}) renders no mask attribute`).toBeTruthy();
      const expected = await maskFor(
        def.puzzle,
        def.stickering,
        primaryAlg(def),
        contextForCase(def),
      );
      expect(mask, def.id).toBe(expected);
    }
  }, 120_000);

  test("no rendered mask ever greys a centre", async () => {
    // Finding 3, asserted on the attribute rather than on `stageMask`: all 41
    // F2L cases used to render `CENTERS:I-----` remapped, because that is
    // cubing.js's own F2L scope.
    for (const def of ALL_CASES) {
      const mask = (await renderedMask(CaseRow, { id: def.id }))!;
      for (const [orbitName, chars] of Object.entries(orbitChars(mask))) {
        if (ORBIT_KINDS[def.puzzle]![orbitName] !== "center") continue;
        expect(chars.includes(GREY), `${def.id} ${orbitName} has a grey centre`).toBe(false);
      }
    }
  }, 120_000);

  test("a centre is never grey on the NO-LADDER path either", async () => {
    // The path /case pages take for a case the alg cannot identify, and the one
    // cubing.js's F2L scope poisons. Asserted on the attribute, not on BASE_MASKS.
    for (const stickering of Object.keys(BASE_MASKS) as (keyof typeof BASE_MASKS)[]) {
      if (stickering === "full") continue;
      const mask = await renderedMask(TwistyPlayer, { alg: "R U R' U'", stickering });
      expect(mask, stickering).toBeTruthy();
      expect(orbitChars(mask!)["CENTERS"]!.includes(GREY), stickering).toBe(false);
    }
    // ...and BASE_MASKS itself is left as cubing.js wrote it: the promotion is
    // in `build`, so it holds for the string that reaches the attribute.
    expect(BASE_MASKS["F2L"]).toContain("CENTERS:I-----");
  });
});

describe("aspect-aware narrowing", () => {
  /**
   * Finding 4: `touchedSlots` used to test permutation AND orientation whatever
   * the stage settled, so an OLL case highlighted corners that were already
   * correctly oriented and merely displaced. The stage's aspect decides.
   */
  const relevant = ALL_CASES.filter((k) => {
    const aspect = STAGES[contextForCase(k).stage].aspect;
    return k.puzzle === "3x3x3" && aspect !== "both";
  });

  test("81 orientation/permutation cases are in scope", () => {
    expect(relevant.length).toBe(81);
  });

  for (const def of relevant) {
    const ctx = contextForCase(def);
    const aspect = STAGES[ctx.stage].aspect;
    test(`${def.id} [${ctx.stage}/${aspect}] highlights only pieces whose ${aspect} is wrong`, async () => {
      const kit = await kit3();
      const alg = primaryAlg(def);
      const chars = orbitChars((await renderedMask(CaseRow, { id: def.id }))!);
      const state = caseStateOf(kit, alg);
      const setup = kit.solved.applyAlg(SETUP_ALG);
      for (const orbitName of ["EDGES", "CORNERS"]) {
        const frame = setup.patternData[orbitName]!.pieces;
        const now = state.patternData[orbitName]!;
        const home = kit.solved.patternData[orbitName]!;
        for (let slot = 0; slot < frame.length; slot++) {
          if (!LIT.has(chars[orbitName]![frame[slot]!]!)) continue;
          const wrong =
            aspect === "orientation"
              ? now.orientation[slot] !== home.orientation[slot]
              : now.pieces[slot] !== home.pieces[slot];
          expect(
            wrong,
            `${orbitName}[${slot}] highlighted but its ${aspect} is already right`,
          ).toBe(true);
        }
      }
    });
  }

  test("the narrowing actually bites: aspect-blind masks would light up more", async () => {
    // The count the audit measured. If this drops to 0 the aspect argument has
    // stopped being threaded through and the test above would pass vacuously.
    let differ = 0;
    for (const def of relevant) {
      const ctx = contextForCase(def);
      const alg = primaryAlg(def);
      const withAspect = (await maskFor(def.puzzle, def.stickering, alg, ctx))!;
      // The same call with the aspect forced back to "both": the stage whose
      // pieces are identical but whose aspect is `both` is `f2l`, so rebuild by
      // hand from the pre-fix rule instead — a piece is touched if EITHER
      // property is off.
      const kit = await kit3();
      const state = caseStateOf(kit, alg);
      const setup = kit.solved.applyAlg(SETUP_ALG);
      const chars = orbitChars(withAspect);
      let blindWouldDiffer = false;
      for (const orbitName of ["EDGES", "CORNERS"]) {
        const frame = setup.patternData[orbitName]!.pieces;
        const now = state.patternData[orbitName]!;
        const home = kit.solved.patternData[orbitName]!;
        for (let slot = 0; slot < frame.length; slot++) {
          const lit = LIT.has(chars[orbitName]![frame[slot]!]!);
          const touchedEither =
            now.pieces[slot] !== home.pieces[slot] ||
            now.orientation[slot] !== home.orientation[slot];
          // Base char must have been a highlight char for this to matter.
          const base = orbitChars(stageMask(ctx)!)[orbitName]![slot]!;
          if (!lit && touchedEither && LIT.has(base)) blindWouldDiffer = true;
        }
      }
      if (blindWouldDiffer) differ++;
    }
    expect(differ).toBe(53);
  }, 60_000);
});

describe("the ladder is wired into every renderer", () => {
  test("contextForPlayer resolves the case an algorithm uniquely identifies", async () => {
    // How /case/[...id] gets the ladder without restating it: 183 of the 185
    // cases are uniquely identified by (puzzle, stickering, algorithm).
    let resolved = 0;
    const unresolved: string[] = [];
    for (const def of ALL_CASES) {
      const ctx = await contextForPlayer(def.puzzle, def.stickering, primaryAlg(def));
      if (ctx) {
        const want = contextForCase(def);
        expect(ctx, def.id).toEqual(want);
        resolved++;
      } else unresolved.push(def.id);
    }
    expect(resolved).toBe(183);
    // ...and the two it refuses are the pair that share `F R U R' U' F'` and
    // sit at DIFFERENT stages. Guessing between them is the yellow-cross bug.
    expect(unresolved.sort()).toEqual(["eo.line", "oll.45"]);
  });

  test("every 3x3 case has a home orientation, so the fallback is big-cube only", async () => {
    for (const def of ALL_CASES.filter((k) => k.puzzle === "3x3x3")) {
      expect(await hasHomeOrientation(def.puzzle, primaryAlg(def)), def.id).toBe(true);
    }
  });

  /**
   * The lesson embeds, read out of the MDX sources rather than retyped: a
   * lesson that loses its `context` prop, or gains a player without one, fails
   * here. The props are then rendered, so the assertion is still on the
   * attribute and not on the source text.
   */
  const EMBED = /<TwistyPlayer\b([\s\S]*?)\/>/g;
  const ATTR = /(\w+)=(?:"([^"]*)"|\{\{\s*ladder:\s*"([^"]+)",\s*stage:\s*"([^"]+)"\s*\}\})/g;

  interface Embed {
    lesson: string;
    props: Record<string, unknown>;
  }

  function lessonEmbeds(): Embed[] {
    const dir = new URL("../src/content/lessons/", import.meta.url);
    const out: Embed[] = [];
    for (const file of readdirSync(dir)
      .filter((f) => f.endsWith(".mdx"))
      .sort()) {
      const src = readFileSync(new URL(file, dir), "utf8");
      for (const [, body] of src.matchAll(EMBED)) {
        const props: Record<string, unknown> = {};
        for (const [, key, value, ladder, stage] of body!.matchAll(ATTR)) {
          props[key!] = ladder ? { ladder, stage } : value;
        }
        out.push({ lesson: file, props });
      }
    }
    return out;
  }

  /**
   * The four beginner-ladder lessons. The beginner method permutes the yellow
   * edges and positions the corners BEFORE orienting them, so these four cannot
   * take the CFOP answer — `ladderOfPhase` would give it to them.
   */
  const BEGINNER_LESSONS: Record<string, string> = {
    "white-corners.mdx": "f1l",
    "yellow-cross.mdx": "eo",
    "align-edges.mdx": "ep",
    "position-corners.mdx": "cp",
  };

  /**
   * The ONLY players allowed to carry no stage, named one by one: a notation
   * demo, where the move itself is the subject and every layer has to stay
   * visible. Listing them by lesson AND algorithm is the point — an allowance
   * granted per FILE would have let the four big-cube demos below hide a lesson
   * that silently lost its `context`, which is the same shape of hole as the
   * one this whole change is fixing. `Rw`/`3Rw`/`Uw` introduce the wide move,
   * not a solving step; the 4x4 player that DOES illustrate a step
   * (`Rw U Rw'`, in the same lesson) names `444-centers` and is masked.
   */
  const NOTATION_DEMOS = new Set([
    "notation.mdx|R U R' U'",
    "finger-tricks.mdx|R U R' U'",
    "444-centers.mdx|Rw",
    "444-centers.mdx|3Rw",
    "444-edge-pairing.mdx|Uw",
    "555-centers-edges.mdx|3Rw",
  ]);

  test("every lesson player either names its step or is a listed notation demo", () => {
    const embeds = lessonEmbeds();
    expect(embeds.length, "the parser found the players").toBe(16);
    const unclassified: string[] = [];
    for (const { lesson, props } of embeds) {
      const ctx = props["context"] as { ladder: string; stage: string } | undefined;
      const demo = NOTATION_DEMOS.has(`${lesson}|${props["alg"]}`);
      if (demo) {
        expect(
          ctx,
          `${lesson} "${props["alg"]}" is a notation demo and must carry no stage`,
        ).toBeUndefined();
      } else if (ctx) {
        expect(LADDERS[ctx.ladder as LadderKey], `${lesson} ladder`).toBeTruthy();
        expect(STAGES[ctx.stage as StageKey], `${lesson} stage`).toBeTruthy();
      } else {
        unclassified.push(`${lesson} "${props["alg"]}"`);
      }
    }
    // No third category. A player that neither names its step nor is a listed
    // notation demo is a case rendering one tier with nobody having decided so.
    expect(unclassified, "players with no stage and no notation-demo entry").toEqual([]);
    for (const [lesson, stage] of Object.entries(BEGINNER_LESSONS)) {
      const mine = embeds.filter((e) => e.lesson === lesson);
      expect(mine.length, `${lesson} has a player`).toBeGreaterThan(0);
      for (const { props } of mine) {
        expect(props["context"], `${lesson} must name the BEGINNER ladder`).toEqual({
          ladder: "beginner",
          stage,
        });
      }
    }
  });

  test("the yellow-cross lesson no longer claims the last-layer corners", async () => {
    // THE BUG, asserted on what the lesson renders. Its player declares
    // stickering "OLL", whose scope covers the corners, so before the ladder was
    // wired in it lit all four of them three lessons before corner orientation
    // is taught. The props come from the MDX, not from this test.
    const embed = lessonEmbeds().find((e) => e.lesson === "yellow-cross.mdx")!;
    expect(embed.props["stickering"], "still declares the OLL scope").toBe("OLL");
    const mask = (await renderedMask(TwistyPlayer, embed.props))!;
    expect(orbitChars(mask)["CORNERS"], "corners are not this step").toBe("DDDDIIII");
    // What it would render without the ladder — the shipped bug, kept here so
    // the gate reads as a comparison rather than a bare constant.
    const { context: _drop, ...noLadder } = embed.props;
    const shipped = (await renderedMask(TwistyPlayer, noLadder))!;
    expect(orbitChars(shipped)["CORNERS"], "all four corners, three lessons early").toBe(
      "DDDDOOOO",
    );
  });

  test("every lesson player renders a mask, or renders none on purpose", async () => {
    for (const { lesson, props } of lessonEmbeds()) {
      const mask = await renderedMask(TwistyPlayer, props);
      if (props["context"]) {
        expect(mask, `${lesson} names a stage but renders no mask`).toBeTruthy();
      }
    }
  });
});

/**
 * The LIMITATION block at the top of lib/ladders.ts is the only part of this
 * feature a test cannot otherwise reach: it is prose about pixels. So the
 * palettes it was measured from ship as data and the ratios are recomputed
 * here — the same discipline as the rest of the suite, applied to a claim.
 *
 * Contrast is what makes the three tiers legible AT ALL. An undocumented pair
 * that reads as one colour is a tier the reader cannot see, so the assertion
 * that matters is COMPLETENESS: nothing under the threshold may be missing.
 */
describe("the documented contrast limits", () => {
  /** Every tier pair on one palette, as {face, pair, ratio}. */
  const allPairs = (palette: Record<string, { highlight: string; dim: string }>, grey: string) =>
    Object.entries(palette).flatMap(([face, { highlight, dim }]) => [
      { face, pair: "H:D" as TierPair, ratio: contrastRatio(highlight, dim) },
      { face, pair: "D:grey" as TierPair, ratio: contrastRatio(dim, grey) },
      { face, pair: "H:grey" as TierPair, ratio: contrastRatio(highlight, grey) },
    ]);

  const THRESHOLD = 2;
  const key = (p: { face: string; pair: TierPair }) => `${p.face} ${p.pair}`;

  test("LOW_CONTRAST_PAIRS is EVERY 3x3 pair under 2:1 — no unreadable pair goes unlisted", () => {
    const under = allPairs(PLAYER_PALETTE, PLAYER_GREY)
      .filter((p) => p.ratio < THRESHOLD)
      .sort((a, b) => a.ratio - b.ratio);
    expect(under.map(key)).toEqual(LOW_CONTRAST_PAIRS.map(key));
  });

  test("each documented ratio is the one the measured palette actually gives", () => {
    const byKey = new Map(allPairs(PLAYER_PALETTE, PLAYER_GREY).map((p) => [key(p), p.ratio]));
    for (const documented of LOW_CONTRAST_PAIRS) {
      const actual = byKey.get(key(documented));
      expect(actual, key(documented)).toBeDefined();
      expect(Number(actual!.toFixed(2)), key(documented)).toBe(documented.ratio);
    }
  });

  test("the pairs are listed worst first, so the top of the list is the worst pair", () => {
    const ratios = LOW_CONTRAST_PAIRS.map((p) => p.ratio);
    expect(ratios).toEqual([...ratios].sort((a, b) => a - b));
    // The claim in the prose: the WORST pair on the 3x3 cube is dim-vs-grey
    // (orange), and highlight-vs-grey — the boundary that carries the most
    // meaning — is the second worst. Both tier boundaries fail, on different
    // faces; an earlier draft claimed the two worst were both highlight-vs-grey.
    expect(LOW_CONTRAST_PAIRS[0]).toEqual({ face: "orange", pair: "D:grey", ratio: 1.09 });
    expect(LOW_CONTRAST_PAIRS[1]).toEqual({ face: "blue", pair: "H:grey", ratio: 1.21 });
    expect(LOW_CONTRAST_PAIRS.filter((p) => p.pair === "H:D").map((p) => p.face)).toEqual([
      "white",
    ]);
  });

  test("the big-cube renderer's trade really does run the other way", () => {
    // PG3D: highlight and dim are CLOSER on every face, dim and grey much
    // further apart, and highlight-vs-grey is the strongest boundary rather
    // than the weakest. That is why the 4x4/5x5 tiering is worth having even
    // though the 3x3 one is the harder read.
    for (const [face, { highlight, dim }] of Object.entries(BIG_CUBE_PALETTE)) {
      const hd = contrastRatio(highlight, dim);
      const dg = contrastRatio(dim, BIG_CUBE_GREY);
      const hg = contrastRatio(highlight, BIG_CUBE_GREY);
      expect(hd, `${face} H:D`).toBeLessThan(THRESHOLD);
      expect(hg, `${face} H:grey`).toBeGreaterThan(hd);
      if (face !== "red") expect(dg, `${face} D:grey`).toBeGreaterThan(3);
    }
    // The numbers the comment prints, to 2dp.
    const at = (a: string, b: string) => Number(contrastRatio(a, b).toFixed(2));
    expect(at(BIG_CUBE_PALETTE["yellow"]!.highlight, BIG_CUBE_PALETTE["yellow"]!.dim)).toBe(1.9);
    expect(at(BIG_CUBE_PALETTE["red"]!.dim, BIG_CUBE_GREY)).toBe(1.46);
    expect(at(BIG_CUBE_PALETTE["green"]!.highlight, BIG_CUBE_GREY)).toBe(6.25);
  });

  test("contrastRatio is WCAG: black on white is 21:1 and a colour on itself is 1:1", () => {
    expect(Number(contrastRatio("#000000", "#FFFFFF").toFixed(2))).toBe(21);
    expect(contrastRatio(PLAYER_GREY, PLAYER_GREY)).toBe(1);
  });

  test("the generated stages.json carries the same limits as the prose", () => {
    // The Python diagram pipeline reads stages.json, not this comment block, so
    // the two must not drift. Both are written from the same measurements.
    const notes: string[] = JSON.parse(
      readFileSync(new URL("../src/data/extracted/stages.json", import.meta.url), "utf8"),
    ).notes;
    const limits = notes.filter((n) => n.startsWith("LIMITATION"));
    expect(limits.length).toBe(2);
    for (const { face, ratio } of LOW_CONTRAST_PAIRS) {
      expect(limits[0], `${face} ${ratio}`).toContain(`${ratio.toFixed(2)}:1`);
    }
    expect(limits[0]).toContain(PLAYER_GREY);
    expect(limits[1]).toContain(BIG_CUBE_GREY);
  });
});
