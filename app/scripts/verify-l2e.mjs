/**
 * 5x5 Last-Two-Edges (L2E) dataset verification — writes
 * src/data/extracted/l2e-raw.json only when every check is clean; exits
 * nonzero otherwise. Runs fully offline (candidate data is pinned below).
 *
 * Sources (per docs/research/tech-brief.md §8 — alg strings are
 * uncopyrightable facts; transcribed 2026-08, SCDB has no API):
 *  - primary: https://speedcubedb.com/a/5x5/L2E — 13 cases "L2E 1".."L2E 13",
 *    algs per case in page order (top-voted first)
 *  - cross-check: https://sarah.cubing.net/5x5x5/l2e (12 algs; presentation:
 *    "two unsolved edges at UF and UB")
 *  - cross-check: https://jperm.net/5x5 — the canonical 5x5 edge parity alg
 *    (note the 3Rw'; it differs from the 4x4 OLL parity form in exactly that
 *    one move — risk #12 in the tech brief)
 *
 * Verification model (all on cubing.js puzzles["5x5x5"].kpuzzle()):
 *
 * L2E happens during reduction edge pairing: centers are done, ten edge
 * groups are paired, corners are NOT yet solved and paired groups need not
 * sit in their home slots (the 3x3 stage places them). So a correct L2E alg
 * must, after cancelling any net whole-cube rotation:
 *  1. preserve every center visually (the 555 kpuzzle gives interchangeable
 *     same-face centers duplicated piece ids, so strict comparison IS visual
 *     comparison — asserted below, not assumed);
 *  2. act on edges so that every non-target edge slot ends holding an INTACT
 *     group — 2 wings + 1 midge of one edge, coherently arranged, possibly
 *     displaced to another slot or flipped as a whole. (Several standard L2E
 *     algs rigidly 4-cycle side edge groups, e.g. "Rw' U' R' U R' F R F' Rw"
 *     cycles the four groups around R — harmless in reduction, so the naive
 *     "non-target edges must be solved in place" rule is provably too strong;
 *     it is still computed and reported per alg as `strict`.)
 *     Valid intact arrangements are calibrated empirically from the 24
 *     whole-cube rotations (for each ordered slot pair exactly 2 rotations
 *     map one to the other: direct and flipped), never hardcoded.
 *  3. have its case content confined to the two target slots: UF and UB,
 *     derived empirically by outer-face membership signatures ("FU"/"BU"),
 *     matching Sarah's stated presentation and SCDB's case images.
 *  4. Corners are FREE: reduction solves corners in the 3x3 stage after L2E.
 *     Mechanical evidence that corner preservation is the wrong requirement:
 *     jperm's canonical parity alg itself permutes corners. Corner behavior
 *     (solved / up-to-AUF / permuted) is reported per alg, and pinned in
 *     EXPECT below so a regression still fails loudly.
 *
 * Checks:
 *  a. kpuzzle structure + notation self-checks (M≡3L, E≡3D, S≡3F, r≡Rw,
 *     l≡Lw, U2'≡U2 — SCDB/Sarah strings need no translation under SiGN;
 *     bare M/E/S are legal on the 555 kpuzzle, unlike the 4x4 case in
 *     extract-algs.mjs) and rotation-calibration sanity (24 arrangements/slot).
 *  b. every alg parses, is legal, and rotation-normalizes (a net trailing
 *     rotation is cancelled on the RIGHT of the forward transformation;
 *     the case state S is its inverse, centers home on both sides).
 *  c. the L2E invariant above, both on the case state and the forward state.
 *  d. round-trip on the DISPLAYED case: synthetic pattern with the ten
 *     non-target groups + corners solved in place and only the target slots
 *     taken from S; alg applied must reach reduction-solved (centers visual +
 *     all 12 slots intact). That pattern is also EXPORTED, as `displayed` —
 *     a delta against solved, one entry per changed edge slot — because it is
 *     the only drawable form of an L2E case and this file owns the reduction
 *     model that produces it. `gen-case-states.mjs` patches the kpuzzle's
 *     default pattern with it and converts to facelets like any other case;
 *     the Python diagram generator draws from there. Pinned to algs[0], the
 *     string that ships.
 *  e. case classes: target-slot content of S, canonicalized over pre-AUF
 *     powers that keep target-home pieces on target (U2 swaps UF<->UB; U/U'
 *     move the case off target so they never qualify). All algs of a case
 *     must agree; all 13 cases must be pairwise distinct.
 *  f. cross-source: jperm's parity alg is verbatim in L2E 6 and differs from
 *     the 4x4 form by exactly the pinned token; every Sarah alg is verified
 *     against a pinned expected outcome (her #5 solves L2E 6 held after y2;
 *     her #8/#9 as published drop SCDB's trailing F2 and mechanically fail —
 *     with F2 restored they verify and map to L2E 8/9).
 *  g. negative controls must fail (4x4 parity form breaks 5x5 centers, etc.).
 *
 * Usage: node scripts/verify-l2e.mjs
 */
import { mkdir, writeFile } from "node:fs/promises";
import { Alg } from "cubing/alg";
import { KPattern } from "cubing/kpuzzle";
import { puzzles } from "cubing/puzzles";

import {
  edgeSlots,
  intactArrangements,
  makeArrangementKey,
  makeKit,
  permutationParity,
  unaliasedCopy,
} from "./lib/kpuzzle-utils.mjs";

// ---------------------------------------------------------------------------
// Pinned data — SCDB 5x5 L2E, algs in page order (top-voted first).
const L2E_CASES = [
  { slug: "l2e-1", name: "L2E 1", algs: ["Rw' U' R' U R' F R F' Rw"] },
  {
    slug: "l2e-2",
    name: "L2E 2",
    algs: ["Lw U' R' U R' F R F' Lw'", "z y Uw F' D' F D' L D L' Uw' y' z'"],
  },
  {
    slug: "l2e-3",
    name: "L2E 3",
    algs: [
      "x' M' U' R' U R' F R F' M x",
      "r' l U' R' U R' F R F' r l'",
      "x' z' E' L' U' L U' F U F' E z x",
    ],
  },
  {
    slug: "l2e-4",
    name: "L2E 4",
    algs: [
      "Rw2 F2 U2 Rw2 U2 F2 Rw2",
      "Rw2 F2 U2 r2 U2 F2 Rw2",
      "z' y' Uw2' R2 F2 Uw2' F2 R2' Uw2'",
      "y x' Uw2 L2 F2 Uw2 F2 L2 Uw2",
    ],
  },
  {
    slug: "l2e-5",
    name: "L2E 5",
    algs: [
      "Rw2 B2 Rw' U2 Rw' U2' x' U2 Rw' U2' Rw U2 Rw' U2' Rw2 U2 x",
      "r2 B2 r' U2 r' U2 x' U2 r' U2 r U2 r' U2 r2 U2",
    ],
  },
  {
    slug: "l2e-6",
    name: "L2E 6",
    // J Perm's string first, deliberately. gen-cases.mjs sends algs[0] to the
    // shipped dataset and demotes the rest to the build-time-only rich file, so
    // whichever sits here is the one the case page, the trainer and the lesson
    // print. It used to be the SCDB primary, which meant the lesson's "open
    // 444.oll-parity and 555.l2e-6 side by side, they are near-twins"
    // instruction compared two different algorithms of different lengths.
    // All four solve the same case (EXPECT below is "sp" four times, so the
    // reorder is inert there) and the first two are visually identical.
    algs: [
      "Rw U2 x Rw U2 Rw U2 3Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'",
      "Rw' U2 3Rw U2 3Rw' F2 Rw2 U2 Rw U2 Rw' U2 F2 Rw2 F2",
      "Rw U2 x Rw U2 Rw U2 Rw' U2 Lw U2 3Rw' U2 Rw U2 Rw' U2 Rw'",
      "Rw2 B2 U2 Lw U2 Rw' U2 Rw U2 F2 Rw F2 Lw' B2 Rw2",
    ],
  },
  {
    slug: "l2e-7",
    name: "L2E 7",
    algs: [
      "y2 Rw U2 Rw U2' x U2 Rw U2' 3Rw' U2 Lw U2' Rw2",
      "Lw' U2 Lw' U2 F2 Lw' F2 Rw U2 Rw' U2 Lw2",
    ],
  },
  {
    slug: "l2e-8",
    name: "L2E 8",
    algs: [
      "Lw2 F2 U2 Lw' U2 Lw2 F2 Lw' U2 Lw2 U2 F2 Lw' F2",
      "l2 F2 U2 r U2 r2 F2 r U2 l2 U2 F2 l' F2",
      "F2 Rw U2 Rw U2' Rw' F2 Rw' U2 Rw' U2' Rw U2 Rw' U2' Rw2",
    ],
  },
  {
    slug: "l2e-9",
    name: "L2E 9",
    algs: [
      "B2 Rw' U2 Rw' U2' Rw B2 Rw U2 Rw U2' Rw' U2 Rw U2' Rw2",
      "r2 F2 U2 r U2 r2 F2 r U2 r2 U2 F2 r F2",
      "x' U2 Rw U2 Rw U2' Rw' F2 Rw' U2 Rw' U2' Rw U2 Rw' U2' Rw2 U2 F2 U2 F2 x",
      "Rw2 F2 U2 Lw' U2 Lw2 F2 Lw' U2 Rw2 U2 F2 Rw F2",
    ],
  },
  { slug: "l2e-10", name: "L2E 10", algs: ["Rw' U2 Rw2 U2 Rw U2 Rw' U2 Rw U2 Rw2 U2 Rw'"] },
  { slug: "l2e-11", name: "L2E 11", algs: ["Rw U2 Rw2 U2 Rw' U2 Rw U2 Rw' U2 Rw2 U2 Rw"] },
  {
    slug: "l2e-12",
    name: "L2E 12",
    algs: [
      "Rw' U2 Rw U2 3Lw' U2 Rw U2 Rw U2' Rw' U2 Rw U2' Rw2 D2 F2 U2 D2",
      "Rw' U2 Rw' U2 B2 Rw' B2 Rw' F2 Lw2 F2 Rw U2 Rw2",
    ],
  },
  {
    slug: "l2e-13",
    name: "L2E 13",
    algs: ["r U R' U' r2 U' R' U r2 U R' U' r'", "Rw U R U' Rw2 U' R U Rw2 U R U' Rw'"],
  },
];

// Parity algs pinned by docs/research/tech-brief.md §8 (jperm.net verbatim).
const EDGE_PARITY_5X5 = "Rw U2 x Rw U2 Rw U2 3Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'";
const OLL_PARITY_4X4 = "Rw U2 x Rw U2 Rw U2 Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'";
// The pairing algorithm the course teaches, from J Perm's 5x5 video
// description. Outer turns only, so it means literally the same thing on a 4x4
// and a 5x5 — unlike anything containing Rw. It has no L2E case of its own (it
// is a mid-pairing tool, not a finisher), so it is pinned by behaviour below
// rather than by appearing in L2E_CASES.
const EDGE_FLIP = "R U R' F R' F' R";
const PARITY_CASE = "l2e-6";
const PARITY_DIFF_TOKEN = 7; // 0-based; "Rw'" (4x4) vs "3Rw'" (5x5)

// Per-alg expected corner/strict profile ("s"=strict holds up to some AUF,
// "-"=only group-rigid; corners: "p"=permuted, "a"=solved up to AUF). Pinned
// so a semantics regression in cubing.js or a bad edit fails loudly.
/** @type {Record<string, string[]>} */
const EXPECT = {
  "l2e-1": ["-p"],
  "l2e-2": ["-p", "-p"],
  "l2e-3": ["-p", "-p", "-p"],
  "l2e-4": ["-a", "-a", "-a", "-a"],
  "l2e-5": ["sp", "sp"],
  "l2e-6": ["sp", "sp", "sp", "sp"],
  "l2e-7": ["sp", "sp"],
  "l2e-8": ["sp", "sp", "sp"],
  "l2e-9": ["sp", "sp", "sp", "sp"],
  "l2e-10": ["sp"],
  "l2e-11": ["sp"],
  "l2e-12": ["-p", "-p"],
  "l2e-13": ["-p", "-p"],
};

// sarah.cubing.net/5x5x5/l2e cross-checks, with pinned expected outcomes.
//  { alg, case } — must verify and map to that SCDB case;
//  { alg, caseUnderY2 } — must verify and map to that case after y2-conjugation
//    (written for the cube held with front/back swapped);
//  { alg, invalid, withSuffix, case } — as published it must FAIL the L2E
//    invariant (Sarah's transcription drops SCDB's trailing F2); with the
//    suffix appended it must verify and map to that case.
const SARAH = [
  { alg: "Rw' U' R' U R' F R F' Rw", case: "l2e-1" },
  { alg: "Lw U' R' U R' F R F' Lw'", case: "l2e-2" },
  { alg: "x' M' U' R' U R' F R F' M", case: "l2e-3" },
  { alg: "Rw2 F2 U2 r2 U2 F2 Rw2", case: "l2e-4" },
  { alg: "Rw U2 Rw U2 Rw' U2 Rw U2 Lw' U2 Rw U2 Rw' U2 x' Rw' U2 Rw' U2 M'", caseUnderY2: "l2e-6" },
  { alg: "Rw U2 Rw U2 Rw' U2 Rw U2 Lw' U2 Lw F2 Rw' F2 Rw' U2 Rw'", case: "l2e-6" },
  { alg: "Lw' U2 Lw' U2 F2 Lw' F2 Rw U2 Rw' U2 Lw2", case: "l2e-7" },
  {
    alg: "Lw2 F2 U2 Lw' U2 Lw2 F2 Lw' U2 Lw2 U2 F2 Lw'",
    invalid: true,
    withSuffix: "F2",
    case: "l2e-8",
  },
  {
    alg: "Rw2 F2 U2 Lw' U2 Lw2 F2 Lw' U2 Rw2 U2 F2 Rw",
    invalid: true,
    withSuffix: "F2",
    case: "l2e-9",
  },
  { alg: "Rw' U2 Rw2 U2 Rw U2 Rw' U2 Rw U2 Rw2 U2 Rw'", case: "l2e-10" },
  { alg: "Rw U2 Rw2 U2 Rw' U2 Rw U2 Rw' U2 Rw2 U2 Rw", case: "l2e-11" },
  { alg: "Rw' U2 Rw' U2 B2 Rw' B2 Rw' F2 Lw2 F2 Rw U2 Rw2", case: "l2e-12" },
];
// Distinct SCDB cases Sarah's page must cover (11 of 13; she has no L2E 5/13).
const SARAH_COVERAGE = 11;

// Controls that must NOT verify (proves the checks can fail).
const NEGATIVE = [
  { label: "4x4 OLL parity form on the 5x5", alg: OLL_PARITY_4X4, expect: "breaks-centers" },
  { label: "sexy move", alg: "R U R' U'", expect: "invariant-fail" },
  { label: "bare inner slice 2R", alg: "2R", expect: "breaks-centers" },
];

// ---------------------------------------------------------------------------
const kp = await puzzles["5x5x5"].kpuzzle();

// Shared rotation/normalization kit; the 555 "centers visually home" test
// spans all three center orbits.
const { solved, toT, ROTATION_T, AUF_T, centersSolved, rightRotNormalize } = makeKit(kp, {
  centerOrbits: ["CENTERS", "CENTERS2", "CENTERS3"],
});
const T = toT;

/** @type {string[]} */
const report = [];
let failures = 0;
/** @param {string} msg */
const fail = (msg) => {
  report.push(`FAIL ${msg}`);
  failures++;
};

/**
 * Cancel an alg's net whole-cube rotation on the RIGHT of its forward
 * transformation (t = Pure ∘ Rot, so Pure = t ∘ Rot⁻¹; a left-composed
 * rotation would conjugate the effect onto the wrong faces). Returns null if
 * no rotation brings centers home (the alg genuinely breaks centers).
 *
 * @param {import("cubing/kpuzzle").KTransformation} t
 */
function rotNormalize(t) {
  try {
    return rightRotNormalize(t);
  } catch {
    return null;
  }
}

// --- empirical slot/orbit derivation ----------------------------------------
// Derived, not tabulated — and derived by the SHARED model, because
// gen-case-states.mjs needs the same three statements for the 4x4 and the two
// copies drifted apart the moment either convention was corrected.
const EDGE_ORBITS = { wingOrbit: "EDGES", midgeOrbit: "EDGES2" };
/** signature ("FU", "BR", …) -> { wings: [i, i], midge: i } */
const SLOTS = edgeSlots(solved, T, EDGE_ORBITS);
const SLOT_NAMES = Object.keys(SLOTS);
const TARGETS = ["FU", "BU"]; // UF + UB, the SCDB/Sarah L2E presentation
const TARGET_PIECES = {
  EDGES: new Set(TARGETS.flatMap((t) => SLOTS[t].wings)),
  EDGES2: new Set(TARGETS.map((t) => SLOTS[t].midge)),
};

/** Content of one edge slot (2 wing stickers + midge, with orientations). */
const arrKey = makeArrangementKey(SLOTS, EDGE_ORBITS);

// Calibrate every valid intact-group arrangement per slot from the 24
// rotations: each ordered (source slot, dest slot) pair is realized by exactly
// two rotations — the direct and the whole-group-flipped placement.
const VALID = intactArrangements(solved, ROTATION_T, SLOTS, arrKey);

/**
 * The DISPLAYED case, as a patch on the solved pattern.
 *
 * This is the export `gen-case-states.mjs` draws 5x5 L2E from, and it exists
 * because the raw case state cannot be drawn: an L2E algorithm is written for
 * a hold partway through reduction, so `alg⁻¹` leaves the two target groups
 * wherever that hold put them (l2e-1 lands them on R and B) and rigidly cycles
 * groups that a solver would not consider part of the case. The displayed
 * pattern is the one this file already builds and round-trips in check (d) —
 * the ten non-target groups and the corners solved in place, only UF and UB
 * taken from the case state — so nothing new is being asserted here, only
 * written down.
 *
 * Emitted as a DELTA against solved rather than as a whole pattern: it is
 * six entries at most (two slots x two wings + one midge), it stays readable
 * in the committed JSON, and a consumer rebuilds it by patching the kpuzzle's
 * own default pattern, so no piece numbering is ever transcribed.
 *
 * @typedef {{ orbit: string; slot: number; piece: number; orientation: number }} Delta
 * @param {Record<string, { pieces: number[]; orientation: number[] }>} data
 * @returns {Delta[]}
 */
function deltaOf(data) {
  /** @type {Delta[]} */
  const out = [];
  for (const orbit of Object.keys(data)) {
    const s = solved.patternData[orbit];
    for (let i = 0; i < s.pieces.length; i++) {
      if (
        data[orbit].pieces[i] === s.pieces[i] &&
        data[orbit].orientation[i] === s.orientation[i]
      ) {
        continue;
      }
      out.push({
        orbit,
        slot: i,
        piece: data[orbit].pieces[i],
        orientation: data[orbit].orientation[i],
      });
    }
  }
  return out;
}

/** @param {import("cubing/kpuzzle").KPattern} p */
const cornersSolvedIn = (p) =>
  solved.patternData.CORNERS.pieces.every(
    (v, i) =>
      p.patternData.CORNERS.pieces[i] === v &&
      p.patternData.CORNERS.orientation[i] === solved.patternData.CORNERS.orientation[i],
  );

/**
 * Case class of a case state S: target-slot content, canonicalized over the
 * pre-AUF powers that keep target-home pieces on target (U2 swaps UF<->UB;
 * U/U' move the case off target so they never qualify — including them would
 * collapse distinct cases onto one generic key).
 *
 * @param {import("cubing/kpuzzle").KTransformation} S
 */
function classKeyOf(S) {
  /** @type {string[]} */
  const keys = [];
  for (const u of AUF_T) {
    const p = solved.applyTransformation(S.applyTransformation(u));
    let onTarget = true;
    for (const tgt of TARGETS) {
      for (const i of SLOTS[tgt].wings) {
        if (!TARGET_PIECES.EDGES.has(p.patternData.EDGES.pieces[i])) onTarget = false;
      }
      if (!TARGET_PIECES.EDGES2.has(p.patternData.EDGES2.pieces[SLOTS[tgt].midge])) {
        onTarget = false;
      }
    }
    if (onTarget) keys.push(JSON.stringify(TARGETS.map((tgt) => arrKey(p, tgt))));
  }
  keys.sort();
  return keys[0];
}

// --- self-checks -------------------------------------------------------------
{
  /** @type {Record<number, number>} */
  const counts = {};
  for (const v of solved.patternData.CENTERS.pieces) counts[v] = (counts[v] ?? 0) + 1;
  if (!Object.values(counts).every((n) => n === 4) || Object.keys(counts).length !== 6) {
    fail("self-check: CENTERS orbit does not use duplicated ids per face");
  }
  /** @type {Record<number, number>} */
  const counts2 = {};
  for (const v of solved.patternData.CENTERS2.pieces) counts2[v] = (counts2[v] ?? 0) + 1;
  if (!Object.values(counts2).every((n) => n === 4) || Object.keys(counts2).length !== 6) {
    fail("self-check: CENTERS2 orbit does not use duplicated ids per face");
  }
  if (SLOT_NAMES.length !== 12) fail(`self-check: ${SLOT_NAMES.length} edge slots, expected 12`);
  for (const slot of SLOT_NAMES) {
    if (SLOTS[slot].wings.length !== 2 || SLOTS[slot].midge < 0) {
      fail(`self-check: slot ${slot} is not 2 wings + 1 midge`);
    }
    if (VALID[slot].size !== 24) {
      fail(`self-check: ${VALID[slot].size} calibrated arrangements at ${slot}, expected 24`);
    }
  }
  for (const t of TARGETS) if (!SLOTS[t]) fail(`self-check: target slot ${t} not derived`);
  // The aliasing `unaliasedCopy` exists for: prove cubing.js still shares one
  // orientation array across same-length orbits (so the helper is not dead
  // code guarding a fixed upstream), and prove the helper breaks it.
  {
    const raw = structuredClone(solved.patternData);
    raw.EDGES.orientation[0] = 1;
    const aliased = raw.CENTERS.orientation[0] === 1 && raw.CENTERS2.orientation[0] === 1;
    const copy = unaliasedCopy(solved.patternData);
    copy.EDGES.orientation[0] = 1;
    if (copy.CENTERS.orientation[0] !== 0 || copy.CENTERS2.orientation[0] !== 0) {
      fail("self-check: unaliasedCopy still shares orientation arrays between orbits");
    }
    if (!aliased) {
      console.warn(
        "note: cubing.js no longer aliases orientation arrays across orbits — " +
          "unaliasedCopy is now redundant, but harmless",
      );
    }
  }
  // Notation identities: SCDB/Sarah strings are valid SiGN as-is (contrast
  // with the 4x4 sets in extract-algs.mjs where bare M needed translation).
  for (const [a, b] of [
    ["M", "3L"],
    ["E", "3D"],
    ["S", "3F"],
    ["r", "Rw"],
    ["l", "Lw"],
    ["U2'", "U2"],
    ["r' l", "x' M'"], // the identity implied by SCDB's own L2E 3 alternates
  ]) {
    if (!T(a).isIdentical(T(b))) fail(`self-check: notation identity ${a} ≡ ${b} does not hold`);
  }
}

// --- per-alg verification ----------------------------------------------------
/**
 * Full analysis of one candidate L2E alg. Returns { error } (parse/legality),
 * { brokenCenters: true }, or { problems: [...], strict, strictAUF, corners,
 * class } — verified iff problems is empty. `problems` is always present so a
 * caller cannot forget the empty-list case.
 *
 * @typedef {object} Analysis
 * @property {string[]} problems - empty means the alg verified
 * @property {string} [error] - parse/legality failure
 * @property {boolean} [brokenCenters]
 * @property {boolean} [strict]
 * @property {number | null} [strictAUF]
 * @property {"solved" | "up-to-AUF" | "permuted"} [corners]
 * @property {string} [class]
 * @property {import("cubing/kpuzzle").KTransformation} [S]
 * @property {Delta[]} [displayed] - the drawable case, as a patch on solved
 *
 * @param {string} algStr
 * @returns {Analysis}
 */
function analyze(algStr) {
  let t;
  try {
    t = T(algStr);
  } catch (e) {
    return { problems: [], error: e instanceof Error ? e.message : String(e) };
  }
  const tp = rotNormalize(t);
  if (tp === null) return { problems: [], brokenCenters: true };
  const S = tp.invert(); // the case state, centers home
  const caseP = solved.applyTransformation(S);
  const fwdP = solved.applyTransformation(tp);
  /** @type {string[]} */
  const problems = [];

  // case content confined to the target slots
  for (const [orbit, homes] of Object.entries(TARGET_PIECES)) {
    for (const tgt of TARGETS) {
      const idxs = orbit === "EDGES" ? SLOTS[tgt].wings : [SLOTS[tgt].midge];
      for (const i of idxs) {
        if (!homes.has(caseP.patternData[orbit].pieces[i])) {
          problems.push(`case ${tgt} holds a non-target piece (${orbit}:${i})`);
        }
      }
    }
  }
  // group rigidity outside the targets, both directions
  for (const slot of SLOT_NAMES) {
    if (TARGETS.includes(slot)) continue;
    if (!VALID[slot].has(arrKey(caseP, slot))) problems.push(`case: broken edge group at ${slot}`);
    if (!VALID[slot].has(arrKey(fwdP, slot))) problems.push(`fwd: broken edge group at ${slot}`);
  }

  // strict spec'd invariant (informational): non-target edges solved in place,
  // up to a net U-layer offset
  let strict = false;
  /** @type {number | null} */
  let strictAUF = null;
  for (let k = 0; k < 4 && !strict; k++) {
    const p = fwdP.applyTransformation(AUF_T[k]);
    let ok = true;
    for (const slot of SLOT_NAMES) {
      if (TARGETS.includes(slot)) continue;
      for (const i of SLOTS[slot].wings) {
        if (
          p.patternData.EDGES.pieces[i] !== solved.patternData.EDGES.pieces[i] ||
          p.patternData.EDGES.orientation[i] !== solved.patternData.EDGES.orientation[i]
        )
          ok = false;
      }
      const m = SLOTS[slot].midge;
      if (
        p.patternData.EDGES2.pieces[m] !== solved.patternData.EDGES2.pieces[m] ||
        p.patternData.EDGES2.orientation[m] !== solved.patternData.EDGES2.orientation[m]
      )
        ok = false;
    }
    if (ok) {
      strict = true;
      strictAUF = k;
    }
  }

  // corner behavior (informational; corners are free during reduction L2E)
  const corners = cornersSolvedIn(fwdP)
    ? "solved"
    : AUF_T.some((u) => cornersSolvedIn(fwdP.applyTransformation(u)))
      ? "up-to-AUF"
      : "permuted";

  // round-trip on the displayed case: only the target slots unsolved
  /** @type {Delta[] | undefined} */
  let displayed;
  if (problems.length === 0) {
    const synth = unaliasedCopy(solved.patternData);
    for (const tgt of TARGETS) {
      for (const i of SLOTS[tgt].wings) {
        synth.EDGES.pieces[i] = caseP.patternData.EDGES.pieces[i];
        synth.EDGES.orientation[i] = caseP.patternData.EDGES.orientation[i];
      }
      const m = SLOTS[tgt].midge;
      synth.EDGES2.pieces[m] = caseP.patternData.EDGES2.pieces[m];
      synth.EDGES2.orientation[m] = caseP.patternData.EDGES2.orientation[m];
    }
    const after = new KPattern(kp, synth).applyTransformation(tp);
    let rt = centersSolved(after);
    for (const slot of SLOT_NAMES) if (!VALID[slot].has(arrKey(after, slot))) rt = false;
    if (!rt) problems.push("round-trip: displayed case + alg is not reduction-solved");
    displayed = deltaOf(synth);
  }

  return { problems, strict, strictAUF, corners, class: classKeyOf(S), S, displayed };
}

const classOf = new Map(); // slug -> class
const classToSlug = new Map(); // class -> slug
/** @type {Map<string, Delta[]>} slug -> the drawable state of algs[0] */
const DISPLAYED = new Map();
let nAlgs = 0;
const strictProfile = { strict: 0, groupRigidOnly: 0 };
const strictAUFs = new Set();
const cornerProfile = { solved: 0, "up-to-AUF": 0, permuted: 0 };

if (L2E_CASES.length !== 13) fail(`expected 13 cases, got ${L2E_CASES.length}`);
if (new Set(L2E_CASES.map((c) => c.slug)).size !== L2E_CASES.length) fail("duplicate slugs");

for (const c of L2E_CASES) {
  if (!/^l2e-\d+$/.test(c.slug) || !/^L2E \d+$/.test(c.name)) {
    fail(`${c.slug}: malformed slug/name`);
  }
  if (c.algs.length === 0) {
    fail(`${c.slug}: no algorithms`);
    continue;
  }
  if (new Set(c.algs).size !== c.algs.length) fail(`${c.slug}: duplicate alg strings`);
  let cls = null;
  /** @type {Delta[] | undefined} */
  let displayed;
  for (const [j, a] of c.algs.entries()) {
    nAlgs++;
    const r = analyze(a);
    if (r.error) {
      fail(`${c.slug}: alg does not parse / is illegal (${r.error}): ${a}`);
      continue;
    }
    if (r.brokenCenters) {
      fail(`${c.slug}: alg breaks centers: ${a}`);
      continue;
    }
    for (const p of r.problems) fail(`${c.slug}: ${p}: ${a}`);
    if (r.problems.length > 0) continue;
    strictProfile[r.strict ? "strict" : "groupRigidOnly"]++;
    // `strict` is only ever set together with strictAUF.
    if (r.strict && r.strictAUF !== null && r.strictAUF !== undefined) {
      strictAUFs.add(["", "U", "U2", "U'"][r.strictAUF]);
    }
    if (r.corners) cornerProfile[r.corners]++;
    const expected = EXPECT[c.slug]?.[j];
    const observed = `${r.strict ? "s" : "-"}${r.corners === "permuted" ? "p" : r.corners === "up-to-AUF" ? "a" : "c"}`;
    if (expected && expected !== observed) {
      fail(`${c.slug} alg ${j}: strict/corner profile ${observed}, pinned ${expected}: ${a}`);
    }
    if (cls === null) cls = r.class;
    else if (r.class !== cls) fail(`${c.slug}: algs disagree on the case (up to pre-AUF): ${a}`);
    // The drawable state is pinned to algs[0] — the one string that ships, and
    // therefore the one a diagram beside it must be solved by. Later algs of
    // the same case can present it a pre-AUF away, which is a different
    // picture of the same case; that is exactly why this is not averaged.
    if (j === 0) displayed = r.displayed;
  }
  if (displayed === undefined) fail(`${c.slug}: no drawable state (algs[0] did not verify)`);
  else DISPLAYED.set(c.slug, displayed);
  if (cls !== null) {
    if (classToSlug.has(cls)) fail(`${c.slug} duplicates case ${classToSlug.get(cls)}`);
    classToSlug.set(cls, c.slug);
    classOf.set(c.slug, cls);
  }
}
if (classToSlug.size !== 13) {
  fail(`${classToSlug.size} distinct case classes, expected 13`);
}

// --- cross-source: jperm parity ---------------------------------------------
{
  const parityCase = L2E_CASES.find((c) => c.slug === PARITY_CASE);
  if (!parityCase) {
    fail(`${PARITY_CASE} is not in the case list`);
  } else if (!parityCase.algs.includes(EDGE_PARITY_5X5)) {
    fail(`jperm 5x5 edge parity alg is not verbatim among ${PARITY_CASE} algs`);
  }
  const t4 = OLL_PARITY_4X4.split(" ");
  const t5 = EDGE_PARITY_5X5.split(" ");
  const diffs = t4.map((tok, i) => (tok !== t5[i] ? i : -1)).filter((i) => i >= 0);
  if (
    t4.length !== t5.length ||
    diffs.length !== 1 ||
    diffs[0] !== PARITY_DIFF_TOKEN ||
    t4[PARITY_DIFF_TOKEN] !== "Rw'" ||
    t5[PARITY_DIFF_TOKEN] !== "3Rw'"
  ) {
    fail("parity algs do not differ by exactly the pinned Rw' -> 3Rw' token");
  }
  const r = analyze(EDGE_PARITY_5X5);
  if (r.error || r.brokenCenters || r.problems.length || classToSlug.get(r.class) !== PARITY_CASE) {
    fail(`jperm parity alg does not verify as ${PARITY_CASE}`);
  }
}

// --- the edge-flip algorithm the course teaches -------------------------------
// Two algorithms plus one technique finish a 5x5. The parity alg is pinned
// above; this is the other one, and because it never appears as an L2E case it
// would otherwise ship in a lesson with nothing verifying it at all.
{
  const toks = EDGE_FLIP.split(" ");
  if (!toks.every((t) => /^[UDFBLR]['2]?$/.test(t))) {
    fail(`edge flip is not outer-turns-only: ${EDGE_FLIP}`);
  }
  // Same seven moves on a 4x4. This is the claim the lessons make on both
  // cubes, and it holds only because there is no layer-count prefix anywhere.
  try {
    const kp4 = await puzzles["4x4x4"].kpuzzle();
    kp4.algToTransformation(new Alg(EDGE_FLIP));
  } catch (e) {
    fail(`edge flip is not legal on a 4x4: ${e instanceof Error ? e.message : e}`);
  }

  const t = T(EDGE_FLIP);
  const p = solved.applyTransformation(t);
  // Centres must come back visually untouched — the whole point of a pairing
  // tool is that it is safe to fire mid-reduction.
  if (!centersSolved(p)) fail("edge flip disturbs the centres");

  // It turns the FR group over in place: its two wings swap AND its midge
  // flips. Anything less is a different algorithm wearing the same name.
  const fr = SLOTS["FR"] ?? SLOTS["RF"];
  if (!fr) {
    fail("no FR slot in the derived slot table");
  } else {
    const wings = p.patternData.EDGES;
    const midges = p.patternData.EDGES2;
    const [w0, w1] = fr.wings;
    const swapped =
      wings.pieces[w0] === solved.patternData.EDGES.pieces[w1] &&
      wings.pieces[w1] === solved.patternData.EDGES.pieces[w0];
    const flipped =
      midges.orientation[fr.midge] !== solved.patternData.EDGES2.orientation[fr.midge];
    if (!swapped) fail("edge flip does not exchange the two FR wings");
    if (!flipped) fail("edge flip does not flip the FR midge");
  }
}

// --- the wing-parity invariant ------------------------------------------------
// Why the course needs exactly two algorithms and not one or three. Every
// outer-turn algorithm is EVEN on the 24 wings, and conjugation cannot change
// permutation parity, so no amount of slice-flip-slice can ever reach an
// odd state. The parity algorithm is the one ODD generator. That is the whole
// of 5x5 parity, and it is asserted here rather than explained in a comment.
{
  /** @param {string} algStr */
  const wingParity = (algStr) => {
    const perm = solved
      .applyTransformation(T(algStr))
      .patternData.EDGES.pieces.map((v, i) => [v, i]);
    const seen = new Array(perm.length).fill(false);
    const src = solved.patternData.EDGES.pieces;
    // Map slot -> slot by matching piece identity; wings are distinguishable
    // enough here because `src` is the solved (identity) arrangement.
    const to = new Array(perm.length);
    for (let i = 0; i < perm.length; i++) to[i] = src.indexOf(perm[i][0]);
    let transpositions = 0;
    for (let i = 0; i < to.length; i++) {
      if (seen[i]) continue;
      let j = i;
      let len = 0;
      while (!seen[j]) {
        seen[j] = true;
        j = to[j];
        len++;
      }
      transpositions += len - 1;
    }
    return transpositions % 2;
  };

  if (wingParity(EDGE_FLIP) !== 0) fail("edge flip is odd on wings — the invariant is wrong");
  for (const outer of ["U", "R", "F", "D", "L", "B"]) {
    if (wingParity(outer) !== 0) fail(`outer turn ${outer} is odd on wings`);
  }
  // Conjugating by a slice cannot change it, which is what makes the claim
  // hold for every slice-flip-slice a learner will ever improvise.
  /** @param {string} m */
  const inv = (m) => (m.endsWith("'") ? m.slice(0, -1) : m.endsWith("2") ? m : `${m}'`);
  for (const setup of ["Uw", "Rw", "3Rw", "Lw'", "Uw2"]) {
    if (wingParity(`${setup} ${EDGE_FLIP} ${inv(setup)}`) !== 0) {
      fail(`the flip conjugated by ${setup} is odd on wings`);
    }
  }
  if (wingParity(EDGE_PARITY_5X5) !== 1) {
    fail("the parity algorithm is EVEN on wings — it cannot then fix parity");
  }
}

// --- what the WRONG algorithm does, because a lesson promises it --------------
// 555-l2e-parity.mdx warns that firing the 4x4 OLL-parity form on a 5x5 breaks
// four edge groups AND the centres. That sentence briefly said the opposite
// about the edges, so it is measured here rather than asserted in prose.
{
  const after = solved.applyTransformation(T(OLL_PARITY_4X4));
  const broken = SLOT_NAMES.filter((s) => !VALID[s].has(arrKey(after, s)));
  if (broken.length !== 4) {
    fail(`the 4x4 parity form breaks ${broken.length} edge groups on a 5x5, expected 4`);
  }
  if (broken.sort().join(" ") !== "BD BU DF FU") {
    fail(`the 4x4 form breaks ${broken.join(" ")}, expected BD BU DF FU`);
  }
  if (centersSolved(after)) fail("the 4x4 parity form leaves 5x5 centres solved — lesson is wrong");
  if (ROTATION_T.some((r) => centersSolved(after.applyTransformation(r)))) {
    fail("a whole-cube rotation DOES restore the centres — the lesson says none does");
  }
}

// --- parity is the only obstruction, per case ---------------------------------
// The wing-parity block above proves the flip can never change parity and the
// parity algorithm always does. This turns that into a statement about the 13
// cases we actually ship: each one is EVEN or ODD, every alternate algorithm of
// a case agrees with it (a case has one parity, not one per algorithm), and one
// application of the parity algorithm clears every odd case. So the only thing
// standing between a learner and a finished 5x5 is the one algorithm they have.
{
  /** @param {import("cubing/kpuzzle").KPattern} pattern */
  const parityOf = (pattern) => permutationParity(pattern, solved, "EDGES");
  /** @param {string} alg */
  const stateOf = (alg) => solved.applyTransformation(T(alg).invert());

  // Measured, and pinned so a data edit that changes a case's parity is loud.
  const ODD = new Set(["l2e-5", "l2e-6", "l2e-7", "l2e-8", "l2e-9", "l2e-10", "l2e-11", "l2e-12"]);
  for (const c of L2E_CASES) {
    const want = ODD.has(c.slug) ? 1 : 0;
    for (const [j, alg] of c.algs.entries()) {
      const got = parityOf(stateOf(alg));
      if (got !== want) {
        fail(`${c.slug} algs[${j}]: wing parity ${got}, expected ${want}`);
      }
    }
    if (want === 1) {
      const cleared = parityOf(stateOf(c.algs[0]).applyTransformation(T(EDGE_PARITY_5X5)));
      if (cleared !== 0) fail(`${c.slug}: one parity application does not clear it`);
    }
  }
}

// --- cross-source: Sarah ------------------------------------------------------
{
  const covered = new Set();
  for (const [i, s] of SARAH.entries()) {
    const label = `sarah #${i + 1}`;
    const r = analyze(s.alg);
    if (r.error) {
      fail(`${label}: does not parse / is illegal (${r.error})`);
      continue;
    }
    if (s.invalid) {
      const bad = r.brokenCenters || r.problems.length > 0;
      if (!bad) fail(`${label}: expected to fail as published, but verifies: ${s.alg}`);
      const fixed = analyze(`${s.alg} ${s.withSuffix}`);
      if (
        fixed.error ||
        fixed.brokenCenters ||
        fixed.problems.length ||
        classToSlug.get(fixed.class) !== s.case
      ) {
        fail(`${label}: with ${s.withSuffix} restored, does not verify as ${s.case}`);
      } else covered.add(s.case);
      continue;
    }
    if (r.brokenCenters || r.problems.length > 0) {
      fail(`${label}: fails the L2E invariant: ${s.alg}`);
      continue;
    }
    if (s.caseUnderY2) {
      if (!r.S) {
        fail(`${label}: verified but carries no case state`);
        continue;
      }
      const y2 = T("y2");
      const Sc = y2.invert().applyTransformation(r.S).applyTransformation(y2);
      if (classToSlug.get(classKeyOf(Sc)) !== s.caseUnderY2) {
        fail(`${label}: not ${s.caseUnderY2} under y2-conjugation`);
      } else covered.add(s.caseUnderY2);
      continue;
    }
    const got = classToSlug.get(r.class);
    if (got !== s.case) fail(`${label}: maps to ${got ?? "no case"}, expected ${s.case}`);
    else covered.add(s.case);
  }
  if (covered.size !== SARAH_COVERAGE) {
    fail(`Sarah cross-check covers ${covered.size} distinct cases, pinned ${SARAH_COVERAGE}`);
  }
}

// --- negative controls --------------------------------------------------------
for (const n of NEGATIVE) {
  const r = analyze(n.alg);
  const outcome = r.error
    ? "illegal"
    : r.brokenCenters
      ? "breaks-centers"
      : r.problems.length > 0
        ? "invariant-fail"
        : "verifies";
  if (outcome !== n.expect) {
    fail(`negative control "${n.label}": outcome ${outcome}, expected ${n.expect}`);
  }
}

// --- report + output ----------------------------------------------------------
if (failures === 0) {
  report.push(
    `✓ 13 L2E cases, ${nAlgs} algs verified on the 5x5 kpuzzle: centers preserved, ` +
      `case confined to UF/UB, non-target edge groups intact (group-rigid), ` +
      `displayed-case round-trips reduction-solved, 13 distinct classes up to pre-AUF`,
  );
  report.push(
    `✓ strict "side edges solved in place" holds for ${strictProfile.strict} algs ` +
      `(net U-layer offset: ${[...strictAUFs].map((u) => u || "none").join(", ")}); ` +
      `${strictProfile.groupRigidOnly} algs rigidly transport intact side groups instead ` +
      `(standard for L2E flip/insert cases)`,
  );
  report.push(
    `✓ corners: ${cornerProfile.permuted} algs permute corners, ` +
      `${cornerProfile["up-to-AUF"]} preserve them up to AUF, ${cornerProfile.solved} solve them ` +
      `— corner freedom is correct here: L2E runs before the 3x3 stage of reduction`,
  );
  report.push(
    `✓ cross-checks: jperm 5x5 edge parity verbatim in ${PARITY_CASE} (3Rw' token pinned vs the ` +
      `4x4 form); all 12 Sarah algs match pinned outcomes (${SARAH_COVERAGE}/13 cases covered; ` +
      `her #5 is l2e-6 held y2; her #8/#9 drop SCDB's trailing F2 and only verify with it ` +
      `restored; she has no l2e-5/l2e-13)`,
  );
  report.push(
    `✓ edge flip ${EDGE_FLIP}: outer turns only, legal on the 4x4 too, centres ` +
      `untouched, turns the FR group over in place — the course's other algorithm, ` +
      `pinned by behaviour because it has no L2E case of its own`,
  );
  report.push(
    `✓ wing parity: every outer turn and the flip (and the flip conjugated by ` +
      `Uw/Rw/3Rw/Lw'/Uw2) are EVEN; the parity alg is ODD — so slice-flip-slice can ` +
      `never reach an odd state and the parity alg is the second generator the ` +
      `puzzle requires, not a convenience`,
  );
  report.push(
    `✓ per-case parity: 8 of the 13 are ODD on wings (l2e-5,6,7,8,9,10,11,12) and 5 are ` +
      `EVEN; every alternate alg agrees with its case; one parity application clears every ` +
      `odd case — so parity is the only obstruction the flip cannot pass`,
  );
  report.push(
    `✓ the 4x4 parity form fired on a 5x5 breaks exactly the four edge groups the lesson ` +
      `names (UB, UF, DF, DB) and wrecks the centres past any rotation`,
  );
  report.push(`✓ ${NEGATIVE.length} negative controls fail as required`);
  report.push(
    `✓ drawable state exported for all ${DISPLAYED.size} cases (${[...DISPLAYED.values()].reduce(
      (n, d) => n + d.length,
      0,
    )} slot patches on solved) — the pattern check (d) round-trips, so a diagram built ` +
      `from it is solved by the algorithm printed beside it`,
  );
}
console.log(report.join("\n"));
if (failures > 0) {
  console.error(
    `\nValidation failed (${failures} failure(s)) — src/data/extracted/l2e-raw.json left untouched`,
  );
  process.exit(1);
}
await mkdir(new URL("../src/data/extracted", import.meta.url), { recursive: true });
await writeFile(
  new URL("../src/data/extracted/l2e-raw.json", import.meta.url),
  JSON.stringify(
    L2E_CASES.map((c) => ({ ...c, displayed: DISPLAYED.get(c.slug) })),
    null,
    1,
  ) + "\n",
);
console.log("\nWrote src/data/extracted/l2e-raw.json (0 failures)");
