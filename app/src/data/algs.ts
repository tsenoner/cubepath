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
export type Stickering = "full" | "Cross" | "F2L" | "LL" | "OLL" | "OCLL" | "PLL" | "ELL";

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
  /**
   * How to recognize the case at the algorithm's execution angle.
   * Lean generated entries omit it — build-time pages read RICH instead.
   */
  recognition?: string;
  algs: AlgVariant[];
  stickering: Stickering;
  puzzle: Puzzle;
  /** e.g. "1/18" — fraction of solves where this exact case appears. */
  probability?: string;
  /** Course phase that introduces the case, e.g. "phase-2", "phase-3". */
  phase: string;
  /** Case ids that should be learned first. */
  prereqs?: string[];
  /** Diagram icon path, e.g. "/diagrams/oll/oll_sune.svg". */
  icon?: string;
}

export const CASES: CaseDef[] = [
  // ── Yellow cross (edge orientation) ────────────────────────────────
  {
    id: "eo.line",
    icon: "/diagrams/oll/oll_line.svg",
    group: "cross-eo",
    name: "Line",
    recognition: "Yellow line through the center — hold it horizontal",
    algs: [{ moves: "F R U R' U' F'", primary: true, note: "F-sexy-F'" }],
    stickering: "OLL",
    puzzle: "3x3x3",
    phase: "phase-1",
  },
  {
    id: "eo.hook",
    icon: "/diagrams/oll/oll_hook.svg",
    group: "cross-eo",
    name: "Hook",
    recognition: "Yellow L-shape — hold the L in the front-right",
    algs: [{ moves: "f R U R' U' f'", primary: true, note: "f-sexy-f' (wide f)" }],
    stickering: "OLL",
    puzzle: "3x3x3",
    phase: "phase-1.5",
  },
  {
    id: "eo.dot",
    icon: "/diagrams/oll/oll_dot.svg",
    group: "cross-eo",
    name: "Dot",
    recognition: "Only the yellow center — no edges oriented",
    algs: [
      { moves: "F R U R' U' F' f R U R' U' f'", primary: true, note: "Line alg, then Hook alg" },
    ],
    stickering: "OLL",
    puzzle: "3x3x3",
    phase: "phase-1",
  },

  // ── Corner orientation (OCLL) ──────────────────────────────────────
  {
    id: "oll.27",
    icon: "/diagrams/oll/oll_sune.svg",
    group: "2look-oll-corners",
    name: "Sune",
    recognition: "1 yellow corner in the front-left, the other 3 twisted clockwise",
    algs: [{ moves: "R U R' U R U2 R'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-2",
  },
  {
    id: "oll.26",
    icon: "/diagrams/oll/oll_antisune.svg",
    group: "2look-oll-corners",
    name: "Anti-Sune",
    recognition: "1 yellow corner in the back-right, the other 3 twisted counter-clockwise",
    algs: [{ moves: "R U2 R' U' R U' R'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  },
  {
    id: "oll.22",
    icon: "/diagrams/oll/oll_pi.svg",
    group: "2look-oll-corners",
    name: "Pi",
    recognition: "0 yellow corners — headlights on the left only",
    algs: [{ moves: "f R U R' U' f' F R U R' U' F'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  },
  {
    id: "oll.23",
    icon: "/diagrams/oll/oll_headlights.svg",
    group: "2look-oll-corners",
    name: "Headlights",
    recognition: "2 yellow corners at the back — headlights facing you",
    algs: [{ moves: "R2 D R' U2 R D' R' U2 R'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  },
  {
    id: "oll.21",
    icon: "/diagrams/oll/oll_double_headlights.svg",
    group: "2look-oll-corners",
    name: "Double Headlights",
    recognition: "0 yellow corners — headlights on the left and the right",
    algs: [{ moves: "R U R' U R U' R' U R U2 R'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "2/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  },
  {
    id: "oll.24",
    icon: "/diagrams/oll/oll_chameleon.svg",
    group: "2look-oll-corners",
    name: "Chameleon",
    recognition: "2 adjacent yellow corners on the right",
    algs: [{ moves: "r U R' U' r' F R F'", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  },
  {
    id: "oll.25",
    icon: "/diagrams/oll/oll_bowtie.svg",
    group: "2look-oll-corners",
    name: "Bowtie",
    recognition: "2 diagonal yellow corners",
    algs: [{ moves: "F' r U R' U' r' F R", primary: true }],
    stickering: "OCLL",
    puzzle: "3x3x3",
    probability: "4/27",
    phase: "phase-3",
    prereqs: ["oll.27"],
  },

  // ── Corner permutation ─────────────────────────────────────────────
  {
    id: "pll.t",
    icon: "/diagrams/pll/pll_tperm.svg",
    group: "2look-pll-corners",
    name: "T-Perm",
    recognition: "Headlights on the left — the two right corners swap",
    algs: [{ moves: "R U R' U' R' F R2 U' R' U' R U R' F'", primary: true }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "4/72",
    phase: "phase-2",
  },
  {
    id: "pll.y",
    icon: "/diagrams/pll/pll_yperm.svg",
    group: "2look-pll-corners",
    name: "Y-Perm",
    recognition: "No headlights anywhere — diagonal corner swap",
    algs: [{ moves: "F R U' R' U' R U R' F' R U R' U' R' F R F'", primary: true }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "4/72",
    phase: "phase-3",
    prereqs: ["pll.t"],
  },

  // ── Edge permutation ───────────────────────────────────────────────
  {
    id: "pll.ub",
    icon: "/diagrams/pll/pll_ub.svg",
    group: "2look-pll-edges",
    name: "Ub",
    recognition: "Solved edge at the back — front edge goes left",
    algs: [{ moves: "R2 U R U R' U' R' U' R' U R'", primary: true }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "4/72",
    phase: "phase-2",
  },
  {
    id: "pll.ua",
    icon: "/diagrams/pll/pll_ua.svg",
    group: "2look-pll-edges",
    name: "Ua",
    recognition: "Solved edge at the back — front edge goes right",
    algs: [{ moves: "M2 U M U2 M' U M2", primary: true, note: "M-slice pair of Ub" }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "4/72",
    phase: "phase-3",
    prereqs: ["pll.ub"],
  },
  {
    id: "pll.h",
    icon: "/diagrams/pll/pll_hperm.svg",
    group: "2look-pll-edges",
    name: "H-Perm",
    recognition: "Both edge pairs swap across — opposite colors face each other",
    algs: [{ moves: "M2 U' M2 U2 M2 U' M2", primary: true }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "1/72",
    phase: "phase-3",
    prereqs: ["pll.ub"],
  },
  {
    id: "pll.z",
    icon: "/diagrams/pll/pll_zperm.svg",
    group: "2look-pll-edges",
    name: "Z-Perm",
    recognition: "Adjacent edge pairs swap — adjacent colors face each other",
    algs: [{ moves: "M' U' M2 U' M2 U' M' U2 M2 U", primary: true }],
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: "2/72",
    phase: "phase-3",
    prereqs: ["pll.ub"],
  },

  // ── The method's own algorithms ────────────────────────────────────
  // The strings the beginner course TEACHES, in the order a reader meets them.
  // For a long time none of them had a case at all, and therefore no
  // /reference row, no /case page, no 3D player and nowhere to look them up.
  // The first pass at fixing that counted bare `<AlgText>` strings with no
  // case — righty, lefty, Niklas and the big-cube edge flip below — and missed
  // everything the lessons print some other way: the two second-layer inserts
  // are composed from righty and lefty in prose, Sune + U is an existing case
  // (oll.27) doing a different job, and the Speed Tricks finishers are printed
  // as four-move halves plus "twice". The guide's Algorithm Reference table and
  // the printed first-solve card carried all of them; /reference did not.
  //
  // They are TRIGGERS, not cases, and the difference is not pedantry: a case is
  // a recognisable state plus the algorithm that solves it, and none of these
  // has a state. That is why they carry `stickering: "full"` — there is no
  // last-layer subset to mask — and why the generic per-stickering invariant in
  // tests/algs.spec.ts has nothing to say about them. Each is pinned there by
  // BEHAVIOUR instead, which is the stronger gate: exactly which pieces it
  // moves, and nothing else. A `full` 3x3 case with no behavioural pin fails
  // the build, so this cannot become a hole to slip an unverified alg through.
  //
  // Every `group` here starts with `beginner-`, which is what /reference's
  // "The Beginner Method" section renders; the stage each group maps to is in
  // scripts/gen-stickering.mjs (`STAGE_OF_GROUP`).
  {
    id: "beginner.righty",
    icon: "/diagrams/steps/corner_right.svg",
    group: "beginner-triggers",
    name: "Righty — the sexy move",
    recognition:
      "The four moves the whole beginner method is built from — corners, second layer, and the last-layer twist",
    algs: [{ moves: "R U R' U'", primary: true, note: "Six in a row return the cube to solved" }],
    stickering: "full",
    puzzle: "3x3x3",
    phase: "phase-1",
  },
  {
    id: "beginner.lefty",
    icon: "/diagrams/steps/corner_front.svg",
    group: "beginner-triggers",
    name: "Lefty — righty mirrored",
    recognition: "Righty in the mirror, run with the left hand — it works the front-left slot",
    algs: [{ moves: "L' U' L U", primary: true }],
    stickering: "full",
    puzzle: "3x3x3",
    phase: "phase-1",
    prereqs: ["beginner.righty"],
  },
  // The second-layer inserts. Both triggers back to back with a cube rotation
  // between them: the first takes the solved corner out of the slot, the
  // mirrored one puts it back with the edge underneath. The guide's table names
  // them "Edge Insert Right" / "Edge Insert Left" and
  // tools/cubepath/src/cubepath/algs.py stores the same strings; the strings
  // here are pinned to that file by tests/algs.spec.ts, so the card and the
  // site cannot print different ones.
  {
    id: "beginner.edge-right",
    icon: "/diagrams/steps/edge_right.svg",
    group: "beginner-edge-insert",
    name: "Edge insert — points right",
    recognition:
      "Upside-down T on the front face and the edge's top sticker matches the RIGHT centre. U, righty, turn the cube, lefty",
    algs: [{ moves: "U R U R' U' y L' U' L U", primary: true }],
    stickering: "full",
    puzzle: "3x3x3",
    phase: "phase-1",
    prereqs: ["beginner.righty", "beginner.lefty"],
  },
  {
    id: "beginner.edge-left",
    icon: "/diagrams/steps/edge_left.svg",
    group: "beginner-edge-insert",
    name: "Edge insert — points left",
    recognition:
      "Upside-down T on the front face and the edge's top sticker matches the LEFT centre. U', lefty, turn the cube, righty",
    algs: [{ moves: "U' L' U' L U y' R U R' U'", primary: true }],
    stickering: "full",
    puzzle: "3x3x3",
    phase: "phase-1",
    prereqs: ["beginner.righty", "beginner.lefty"],
  },
  // Sune in its BEGINNER job. The same seven moves are `oll.27`, a corner
  // orientation case with a corner-orientation picture, and that is the only
  // row a reader looking for "the thing that swaps two yellow edges" used to
  // find. The trailing U is part of the tool: bare Sune is a three-cycle of the
  // yellow edges and on its own aligns no adjacent pair from any hold. The
  // printed card once said "hold them back and left" and printed Sune bare;
  // from that hold no number of U turns after it helps (measured), and from
  // the right hold the missing U is only survivable because Step 5's loop
  // re-counts with U turns anyway.
  {
    id: "beginner.sune-u",
    icon: "/diagrams/steps/align_adjacent.svg",
    group: "beginner-edge-swap",
    name: "Sune + U — the edge swap",
    recognition:
      "Two yellow edges already over their centres, side by side: hold them BACK and RIGHT. Swaps the front and left edges and leaves the cross alone; the corners scramble, ignore them",
    algs: [{ moves: "R U R' U R U2 R' U", primary: true, note: "Sune, then a single U" }],
    stickering: "full",
    puzzle: "3x3x3",
    phase: "phase-1",
  },
  {
    id: "beginner.niklas",
    icon: "/diagrams/steps/corner_cycle.svg",
    group: "beginner-corner-cycle",
    name: "Niklas — the corner cycle",
    recognition:
      "Holds the front-left corner in its seat and cycles the other three: front-right → back-right → back-left. Square the top with one U first",
    algs: [{ moves: "R U' L' U R' U' L", primary: true, note: "Then a single U" }],
    stickering: "full",
    puzzle: "3x3x3",
    phase: "phase-1",
  },
  // The Speed Tricks corner finishers: Step 7's righty-and-flip without the
  // flip. Stored DOUBLED, as algs.py stores them — cubing notation has no
  // repeat operator, and the four-move half on its own orients nothing. The
  // second is the first undone, so a reader who learns one has the other.
  {
    id: "beginner.twist-right",
    icon: "/diagrams/steps/orient_right.svg",
    group: "beginner-corner-twist",
    name: "Corner twist — yellow faces right",
    recognition:
      "Yellow on top, an unsolved corner at the front-right with its yellow sticker facing RIGHT. Twists that one corner; turn only U between corners",
    algs: [{ moves: "R' D' R D R' D' R D", primary: true, note: "R' D' R D, twice" }],
    stickering: "full",
    puzzle: "3x3x3",
    phase: "phase-1.5",
    prereqs: ["beginner.righty"],
  },
  {
    id: "beginner.twist-front",
    icon: "/diagrams/steps/orient_front.svg",
    group: "beginner-corner-twist",
    name: "Corner twist — yellow faces front",
    recognition:
      "Yellow on top, an unsolved corner at the front-right with its yellow sticker facing FRONT. The right-hand twist undone, move for move",
    algs: [{ moves: "D' R' D R D' R' D R", primary: true, note: "D' R' D R, twice" }],
    stickering: "full",
    puzzle: "3x3x3",
    phase: "phase-1.5",
    prereqs: ["beginner.twist-right"],
  },

  // ── Big cubes ──────────────────────────────────────────────────────
  {
    id: "444.edge-flip",
    icon: "/diagrams/steps/step_444_flip.svg",
    group: "bigcube-pairing",
    name: "The edge flip",
    recognition:
      "Turns the front-right edge pair over in place. Seven outer turns, nothing wide — so it cannot break a pair you have already made, and it means the same thing on a 5×5",
    algs: [{ moves: "R U R' F R' F' R", primary: true }],
    stickering: "full",
    puzzle: "4x4x4",
    phase: "444",
  },
  {
    id: "444.oll-parity",
    icon: "/diagrams/444-parity/444_oll_parity.svg",
    group: "444-parity",
    name: "OLL Parity (4×4)",
    recognition:
      "One edge pair on the last layer is flipped over — its two halves show the side colour on top. No 3×3 can reach this",
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
  },
];

import { GENERATED_CASES } from "./fullsets.gen";

/**
 * The complete dataset: curated course cases take precedence over generated
 * entries with the same id (they carry hand-written recognition + phases);
 * generated entries fill in the full OLL/PLL/4x4 sets.
 */
export const CURATED_IDS: ReadonlySet<string> = new Set(CASES.map((k) => k.id));
export const ALL_CASES: CaseDef[] = [
  ...CASES,
  ...GENERATED_CASES.filter((k) => !CURATED_IDS.has(k.id)),
];

export const caseById = new Map(ALL_CASES.map((k) => [k.id, k]));

/**
 * Full-set membership by id shape. The curated 2-look entries (oll.21–27,
 * pll.t/y/ua/ub/h/z) carry curated phases ("phase-2"/"phase-3"), so a phase
 * test would undercount the full sets — the id shape is the truth.
 */
export const isFullOll = (def: CaseDef): boolean => /^oll\.\d+$/.test(def.id);
export const isFullPll = (def: CaseDef): boolean => def.id.startsWith("pll.");

export function primaryAlg(def: CaseDef): string {
  const p = def.algs.find((a) => a.primary) ?? def.algs[0];
  if (!p) throw new Error(`case ${def.id} has no algorithms`);
  return p.moves;
}
