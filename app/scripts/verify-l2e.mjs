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
 *     all 12 slots intact).
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
import { KPattern } from "cubing/kpuzzle";
import { puzzles } from "cubing/puzzles";

import { makeKit } from "./lib/kpuzzle-utils.mjs";

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
    algs: [
      "Rw' U2 3Rw U2 3Rw' F2 Rw2 U2 Rw U2 Rw' U2 F2 Rw2 F2",
      "Rw U2 x Rw U2 Rw U2 3Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'",
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
const PARITY_CASE = "l2e-6";
const PARITY_DIFF_TOKEN = 7; // 0-based; "Rw'" (4x4) vs "3Rw'" (5x5)

// Per-alg expected corner/strict profile ("s"=strict holds up to some AUF,
// "-"=only group-rigid; corners: "p"=permuted, "a"=solved up to AUF). Pinned
// so a semantics regression in cubing.js or a bad edit fails loudly.
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
  { alg: "Lw2 F2 U2 Lw' U2 Lw2 F2 Lw' U2 Lw2 U2 F2 Lw'", invalid: true, withSuffix: "F2", case: "l2e-8" },
  { alg: "Rw2 F2 U2 Lw' U2 Lw2 F2 Lw' U2 Rw2 U2 F2 Rw", invalid: true, withSuffix: "F2", case: "l2e-9" },
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

const report = [];
let failures = 0;
const fail = (msg) => {
  report.push(`FAIL ${msg}`);
  failures++;
};

/**
 * Cancel an alg's net whole-cube rotation on the RIGHT of its forward
 * transformation (t = Pure ∘ Rot, so Pure = t ∘ Rot⁻¹; a left-composed
 * rotation would conjugate the effect onto the wrong faces). Returns null if
 * no rotation brings centers home (the alg genuinely breaks centers).
 */
function rotNormalize(t) {
  try {
    return rightRotNormalize(t);
  } catch {
    return null;
  }
}

// --- empirical slot/orbit derivation ----------------------------------------
const FACES = ["U", "D", "L", "R", "F", "B"];
const faceP = Object.fromEntries(
  FACES.map((f) => [f, solved.applyTransformation(T(f)).patternData]),
);
const SLOTS = {}; // signature ("FU", "BR", …) -> { wings: [i, i], midge: i }
for (const orbit of ["EDGES", "EDGES2"]) {
  const s = solved.patternData[orbit];
  for (let i = 0; i < s.pieces.length; i++) {
    const sig = FACES.filter(
      (f) =>
        faceP[f][orbit].pieces[i] !== s.pieces[i] ||
        faceP[f][orbit].orientation[i] !== s.orientation[i],
    )
      .sort()
      .join("");
    SLOTS[sig] ??= { wings: [], midge: -1 };
    if (orbit === "EDGES") SLOTS[sig].wings.push(i);
    else SLOTS[sig].midge = i;
  }
}
const SLOT_NAMES = Object.keys(SLOTS);
const TARGETS = ["FU", "BU"]; // UF + UB, the SCDB/Sarah L2E presentation
const TARGET_PIECES = {
  EDGES: new Set(TARGETS.flatMap((t) => SLOTS[t].wings)),
  EDGES2: new Set(TARGETS.map((t) => SLOTS[t].midge)),
};

/** Content of one edge slot (2 wing stickers + midge, with orientations). */
const arrKey = (p, slot) => {
  const { wings, midge } = SLOTS[slot];
  const E = p.patternData.EDGES;
  const M = p.patternData.EDGES2;
  return JSON.stringify([
    wings.map((i) => [E.pieces[i], E.orientation[i]]),
    M.pieces[midge],
    M.orientation[midge],
  ]);
};

// Calibrate every valid intact-group arrangement per slot from the 24
// rotations: each ordered (source slot, dest slot) pair is realized by exactly
// two rotations — the direct and the whole-group-flipped placement.
const VALID = {};
for (const slot of SLOT_NAMES) VALID[slot] = new Set();
for (const r of ROTATION_T) {
  const p = solved.applyTransformation(r);
  for (const slot of SLOT_NAMES) VALID[slot].add(arrKey(p, slot));
}

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
 */
function classKeyOf(S) {
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
  const counts = {};
  for (const v of solved.patternData.CENTERS.pieces) counts[v] = (counts[v] ?? 0) + 1;
  if (!Object.values(counts).every((n) => n === 4) || Object.keys(counts).length !== 6) {
    fail("self-check: CENTERS orbit does not use duplicated ids per face");
  }
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
 * class } — verified iff problems is empty.
 */
function analyze(algStr) {
  let t;
  try {
    t = T(algStr);
  } catch (e) {
    return { error: String(e.message) };
  }
  const tp = rotNormalize(t);
  if (tp === null) return { brokenCenters: true };
  const S = tp.invert(); // the case state, centers home
  const caseP = solved.applyTransformation(S);
  const fwdP = solved.applyTransformation(tp);
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
  if (problems.length === 0) {
    const synth = structuredClone(solved.patternData);
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
  }

  return { problems, strict, strictAUF, corners, class: classKeyOf(S), S };
}

const classOf = new Map(); // slug -> class
const classToSlug = new Map(); // class -> slug
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
    if (r.strict) strictAUFs.add(["", "U", "U2", "U'"][r.strictAUF]);
    cornerProfile[r.corners]++;
    const expected = EXPECT[c.slug]?.[j];
    const observed = `${r.strict ? "s" : "-"}${r.corners === "permuted" ? "p" : r.corners === "up-to-AUF" ? "a" : "c"}`;
    if (expected && expected !== observed) {
      fail(`${c.slug} alg ${j}: strict/corner profile ${observed}, pinned ${expected}: ${a}`);
    }
    if (cls === null) cls = r.class;
    else if (r.class !== cls) fail(`${c.slug}: algs disagree on the case (up to pre-AUF): ${a}`);
  }
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
  if (!parityCase.algs.includes(EDGE_PARITY_5X5)) {
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
  report.push(`✓ ${NEGATIVE.length} negative controls fail as required`);
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
  JSON.stringify(L2E_CASES, null, 1) + "\n",
);
console.log("\nWrote src/data/extracted/l2e-raw.json (0 failures)");
