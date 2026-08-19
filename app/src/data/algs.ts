/**
 * Canonical case/algorithm dataset — the single source of truth.
 *
 * Every case's primary algorithm is machine-verified in tests/algs.spec.ts:
 * applying the algorithm to its own inverse-scrambled state must solve the
 * case's stickering mask on the cubing.js kpuzzle. A wrong algorithm cannot
 * ship — the build fails first.
 */

export type Puzzle = "3x3x3" | "4x4x4" | "5x5x5";

/** twisty-player experimental-stickering values used by Cubepath. */
export type Stickering =
  | "full"
  | "Cross"
  | "F2L"
  | "LL"
  | "OLL"
  | "OCLL"
  | "PLL"
  | "ELL";

export interface AlgVariant {
  moves: string;
  /** Exactly one variant per case is primary. */
  primary?: boolean;
  note?: string;
}

export interface CaseDef {
  /** Canonical id, e.g. "oll.27", "pll.t", "eo.line", "444.oll-parity". */
  id: string;
  /** Grouping for course structure and the trainer, e.g. "2look-oll-corners". */
  group: string;
  name: string;
  /** How to recognize the case at the algorithm's execution angle. */
  recognition: string;
  algs: AlgVariant[];
  stickering: Stickering;
  puzzle: Puzzle;
  /** e.g. "1/18" — fraction of solves where this exact case appears. */
  probability?: string;
  /** Course phase that introduces the case, e.g. "phase-2", "phase-3". */
  phase: string;
  /** Case ids that should be learned first. */
  prereqs?: string[];
}

const c = (def: CaseDef): CaseDef => def;

export const CASES: CaseDef[] = [
  // ── Yellow cross (edge orientation) ────────────────────────────────
  c({
    id: "eo.line",
    group: "cross-eo",
    name: "Line",
    recognition: "Yellow line through the center — hold it horizontal",
    algs: [{ moves: "F R U R' U' F'", primary: true, note: "F-sexy-F'" }],
    stickering: "OLL",
    puzzle: "3x3x3",
    phase: "phase-1",
  }),
  c({
    id: "eo.hook",
    group: "cross-eo",
    name: "Hook",
    recognition: "Yellow L-shape — hold the L in the front-right",
    algs: [{ moves: "f R U R' U' f'", primary: true, note: "f-sexy-f' (wide f)" }],
    stickering: "OLL",
    puzzle: "3x3x3",
    phase: "phase-1.5",
  }),
  c({
    id: "eo.dot",
    group: "cross-eo",
    name: "Dot",
    recognition: "Only the yellow center — no edges oriented",
    algs: [
      { moves: "F R U R' U' F' f R U R' U' f'", primary: true, note: "Line alg, then Hook alg" },
    ],
    stickering: "OLL",
    puzzle: "3x3x3",
    phase: "phase-1",
  }),

  // ── Corner orientation (OCLL) ──────────────────────────────────────
  c({
    id: "oll.27",
    group: "2look-oll-corners",
    name: "Sune",
    recognition: "1 yellow corner in the front-left, the other 3 twisted clockwise",
    algs: [{ moves: "R U R' U R U2 R'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-2",
  }),
  c({
    id: "oll.26",
    group: "2look-oll-corners",
    name: "Anti-Sune",
    recognition: "1 yellow corner in the back-right, the other 3 twisted counter-clockwise",
    algs: [{ moves: "R U2 R' U' R U' R'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  }),
  c({
    id: "oll.22",
    group: "2look-oll-corners",
    name: "Pi",
    recognition: "0 yellow corners — headlights on the left only",
    algs: [{ moves: "f R U R' U' f' F R U R' U' F'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  }),
  c({
    id: "oll.23",
    group: "2look-oll-corners",
    name: "Headlights",
    recognition: "2 yellow corners at the back — headlights facing you",
    algs: [{ moves: "R2 D R' U2 R D' R' U2 R'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  }),
  c({
    id: "oll.21",
    group: "2look-oll-corners",
    name: "Double Headlights",
    recognition: "0 yellow corners — headlights on the left and the right",
    algs: [{ moves: "R U R' U R U' R' U R U2 R'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "2/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  }),
  c({
    id: "oll.24",
    group: "2look-oll-corners",
    name: "Chameleon",
    recognition: "2 adjacent yellow corners on the right",
    algs: [{ moves: "r U R' U' r' F R F'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  }),
  c({
    id: "oll.25",
    group: "2look-oll-corners",
    name: "Bowtie",
    recognition: "2 diagonal yellow corners",
    algs: [{ moves: "F' r U R' U' r' F R", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  }),

  // ── Corner permutation ─────────────────────────────────────────────
  c({
    id: "pll.t",
    group: "2look-pll-corners",
    name: "T-Perm",
    recognition: "Headlights on the left — the two right corners swap",
    algs: [{ moves: "R U R' U' R' F R2 U' R' U' R U R' F'", primary: true }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "4/72",
    phase: "phase-2",
  }),
  c({
    id: "pll.y",
    group: "2look-pll-corners",
    name: "Y-Perm",
    recognition: "No headlights anywhere — diagonal corner swap",
    algs: [{ moves: "F R U' R' U' R U R' F' R U R' U' R' F R F'", primary: true }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "4/72",
    phase: "phase-3",
    prereqs: ["pll.t"],
  }),

  // ── Edge permutation ───────────────────────────────────────────────
  c({
    id: "pll.ub",
    group: "2look-pll-edges",
    name: "Ub",
    recognition: "Solved edge at the back — front edge goes left",
    algs: [{ moves: "R2 U R U R' U' R' U' R' U R'", primary: true }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "4/72",
    phase: "phase-2",
  }),
  c({
    id: "pll.ua",
    group: "2look-pll-edges",
    name: "Ua",
    recognition: "Solved edge at the back — front edge goes right",
    algs: [{ moves: "M2 U M U2 M' U M2", primary: true, note: "M-slice pair of Ub" }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "4/72",
    phase: "phase-3",
    prereqs: ["pll.ub"],
  }),
  c({
    id: "pll.h",
    group: "2look-pll-edges",
    name: "H-Perm",
    recognition: "Both edge pairs swap across — opposite colors face each other",
    algs: [{ moves: "M2 U' M2 U2 M2 U' M2", primary: true }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "1/72",
    phase: "phase-3",
    prereqs: ["pll.ub"],
  }),
  c({
    id: "pll.z",
    group: "2look-pll-edges",
    name: "Z-Perm",
    recognition: "Adjacent edge pairs swap — adjacent colors face each other",
    algs: [{ moves: "M' U' M2 U' M2 U' M' U2 M2 U", primary: true }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "2/72",
    phase: "phase-3",
    prereqs: ["pll.ub"],
  }),

  // ── Big cubes (M0 proof seeds — full courses land in M5) ───────────
  c({
    id: "444.oll-parity",
    group: "444-parity",
    name: "OLL Parity (4×4)",
    recognition: "A single flipped edge pair on the last layer — impossible on a 3×3",
    algs: [
      {
        moves: "Rw U2 x Rw U2 Rw U2 Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'",
        primary: true,
      },
    ],
    stickering: "full",
    puzzle: "4x4x4",
    probability: "1/2",
    phase: "444",
  }),
];

import { GENERATED_CASES } from "./fullsets.gen";

/**
 * The complete dataset: curated course cases take precedence over generated
 * entries with the same id (they carry hand-written recognition + phases);
 * generated entries fill in the full OLL/PLL/4x4 sets.
 */
const curatedIds = new Set(CASES.map((k) => k.id));
export const ALL_CASES: CaseDef[] = [
  ...CASES,
  ...GENERATED_CASES.filter((k) => !curatedIds.has(k.id)),
];

export const caseById = new Map(ALL_CASES.map((k) => [k.id, k]));

export function primaryAlg(def: CaseDef): string {
  const p = def.algs.find((a) => a.primary) ?? def.algs[0];
  if (!p) throw new Error(`case ${def.id} has no algorithms`);
  return p.moves;
}
