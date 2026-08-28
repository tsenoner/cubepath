/**
 * The progressive stage ladder: ordering, and nothing else.
 *
 * The three tiers a diagram can put a piece in:
 *   HIGHLIGHT  what this step solves
 *   DIM        solved by an earlier step — must be preserved, not re-solved
 *   GREY       not yet reached
 *
 * Three facts shape this module.
 *
 * 1. THERE ARE TWO 3x3 LADDERS. The beginner method permutes the yellow edges
 *    and positions the corners before orienting them (align-edges order 70 ->
 *    position-corners 80 -> orient-corners 90); CFOP orients first. The SAME
 *    algorithm therefore sits at different stages in the two — Sune is the
 *    highlight of `oc` under CFOP, and appears inside the `ep` step in the
 *    beginner lesson — so the tier assignment cannot live on `CaseDef`. The
 *    STAGE comes from the case's `group`; the LADDER comes from the calling
 *    context (a lesson may override it), defaulting to the case's `phase`.
 *
 * 2. "DONE" IS NOT A BOOLEAN for a last-layer piece: OLL orients without
 *    permuting. Every stage therefore carries an ASPECT — both / orientation /
 *    permutation — and cubing.js's char set already encodes exactly that
 *    distinction (`O` = top colour only, `P` = top settled, sides are what is
 *    left, `o` = the dim form of `O`). The aspect is not decoration: it is also
 *    what `maskFor` narrows on, so an OLL case highlights the MISORIENTED
 *    pieces and not every piece the algorithm happens to move.
 *
 * 3. A CENTRE IS NEVER GREY. Grey means "the method has not reached this
 *    piece"; a centre is fixed by definition and is the frame every recognition
 *    cue on the site is written against. Exactly one stage per ladder
 *    highlights the centres — the first that claims them (`cross` on the 3x3
 *    ladders, `444-centers`/`555-centers` on the big-cube ones) — and every
 *    later stage leaves them DIM. The generator builds this in; `stickering.ts`
 *    holds the same line for the no-ladder path, where cubing.js's own `F2L`
 *    scope would otherwise grey the U centre out on all 41 F2L cases.
 *
 * All of the data below is read from src/data/extracted/stages.json, which
 * scripts/gen-stickering.mjs derives from cubing.js itself (piece sets come out
 * of layer-move algebra — no slot index is ever typed) and which the Python
 * diagram pipeline is meant to consume too. Its schema is documented at the top
 * of that generator. Regenerate with `npm run gen:stickering`; never hand-edit.
 *
 * ── LIMITATION, stated here because it is not fixable in code ────────────────
 * The three tiers are told apart by COLOUR ALONE, and on cubing.js's palette
 * several of those colours are the same tone. The palettes below are measured
 * off decoded screenshots of the player, not read off a spec sheet, and
 * `PLAYER_PALETTE` / `BIG_CUBE_PALETTE` at the bottom of this file carry them
 * as data so `LOW_CONTRAST_PAIRS` can be recomputed rather than believed —
 * tests/algs.spec.ts recomputes every ratio and fails if this prose drifts.
 *
 * WHICH PAIRS ARE UNREADABLE (3x3 renderer, every pair under WCAG 2:1, worst
 * first). "H" is highlight, "D" dim, grey is #666666:
 *   1.09:1  orange  D #885500 vs grey        already-solved vs not-yet-reached
 *   1.21:1  blue    H #2266FF vs grey        solve-THIS vs ignore-that
 *   1.24:1  green   D #008800 vs grey
 *   1.36:1  white   D #DDDDDD vs H #FFFFFF   the two tiers of one face
 *   1.44:1  red     H #FF0000 vs grey
 *   1.52:1  yellow  D #888800 vs grey
 *   1.97:1  blue    D #113388 vs grey
 * Read that as: BOTH tier boundaries fail, and they fail on different faces.
 * Dim-vs-grey is the worst pair on the cube (orange, 1.09:1) and also the most
 * common, since every stage but each ladder's first and last has both tiers on
 * screen at once. Highlight-vs-grey is the boundary that carries the most
 * meaning — it is the one saying "solve this, ignore that" — and it fails
 * second-worst, on blue; it bites hardest at `cross` and `f1l`, where the grey
 * tier is at its largest. Highlight-vs-dim fails on exactly one face, white,
 * which is why the clash is confined to `f1l` and `f2l`: those are the two
 * stages that put a dim white cross facelet beside a highlighted white corner.
 * Every later stage has the whole D face in one tier.
 *
 * BIG CUBES ARE A DIFFERENT RENDERER and a different palette: 4x4 and 5x5 go
 * through PG3D, whose dim is a ~0.73 multiply rather than the 3x3 renderer's
 * near-black, and whose grey is #444444. Measured off a 4x4 OLL-parity player:
 *   yellow  #F4F400 / #B3B300   H:D 1.90:1   D:grey 4.34:1   H:grey 8.25:1
 *   green   #44EE00 / #2FAF00   H:D 1.86:1   D:grey 3.36:1   H:grey 6.25:1
 *   red     #FF0000 / #BC0000   H:D 1.67:1   D:grey 1.46:1   H:grey 2.44:1
 * The trade runs the other way there: dim and highlight are closer (all three
 * faces under 2:1), but dim and grey are much further apart on every face
 * except red — and highlight-vs-grey, the boundary that matters most, is the
 * strongest of the three rather than the weakest.
 *
 * cubing 0.63.3 has no cube-palette API (`colorScheme` is the widget's
 * light/dark chrome), so none of this can be tuned in the player. The
 * mitigation is that the worst-affected stages are illustrated by static SVGs,
 * where the palette is ours — which is why the shared artifact between the two
 * renderers is stages.json's TIER ASSIGNMENT and never the colours. That Python
 * side lands after the current diagram wave; this file is the seam.
 */
import stagesFile from "../data/extracted/stages.json";

export type Aspect = "both" | "orientation" | "permutation";
export type Tier = "highlight" | "dim" | "grey";
/** What a piece is, derived from how many faces move it (3 / 2 / 1). */
export type OrbitKind = "corner" | "edge" | "center";

/** Stage keys, derived from the generated file rather than retyped. */
export type StageKey = keyof (typeof stagesFile)["stages"];
/** Ladder keys, likewise. */
export type LadderKey = keyof (typeof stagesFile)["ladders"];

/** Which step of which method a diagram is illustrating. */
export interface StageContext {
  ladder: LadderKey;
  stage: StageKey;
}

interface StageEntry {
  aspect: Aspect;
  /** The puzzles this stage has a derived piece set for. */
  puzzles: string[];
  members: string[] | null;
  /** puzzle -> orbit -> slot indices. */
  pieces: Record<string, Record<string, number[]> | null>;
  pieceNames: Record<string, Record<string, string[]> | null>;
}

interface PuzzleGeometry {
  orbits: { name: string; numPieces: number }[];
  orbitKinds: Record<string, OrbitKind>;
  /** orbit -> slot -> cubie under the setup rotation. */
  frame: Record<string, number[]>;
  pieceNames: Record<string, string[]>;
}

/** The loose shape of the generated file, for lookups by a computed key. */
const RAW = stagesFile as unknown as {
  schema: string;
  setupAlg: string;
  puzzles: Record<string, PuzzleGeometry>;
  baseMasks: Record<string, string>;
  tierChars: Record<Tier, Record<Aspect, string>>;
  stages: Record<string, StageEntry>;
  ladders: Record<string, string[]>;
  ladderPuzzle: Record<string, string>;
  renderedLadders: string[];
  stageOfGroup: { kind: "exact" | "prefix"; key: string; stage: string }[];
  ladderOfPhase: Record<string, string>;
  defaultLadder: string;
  masks: Record<string, Record<string, string>>;
};

/** Bumped by the generator whenever a field changes shape. */
export const STAGES_SCHEMA = RAW.schema;

/** Ladder -> its stages, in order. The only hand-written data in the pipeline. */
export const LADDERS = RAW.ladders as Record<LadderKey, readonly StageKey[]>;

/** Ladder -> the puzzle it is a ladder for. */
export const LADDER_PUZZLE = RAW.ladderPuzzle as Record<LadderKey, string>;

/** Stage -> aspect, the puzzles it exists on, and its piece set on each. */
export const STAGES = RAW.stages as Record<StageKey, StageEntry>;

/**
 * tier -> aspect -> serialized mask char. The `dim` row is exactly the `QUIET`
 * demotion that already ships in stickering.ts; tests/algs.spec.ts asserts the
 * two agree rather than trusting the coincidence.
 */
export const TIER_CHARS = RAW.tierChars;

/** Puzzle -> orbits, piece kinds, setup frame and geometric slot names. */
export const PUZZLE_GEOMETRY: Record<string, PuzzleGeometry> = RAW.puzzles;

/**
 * Puzzle -> orbit -> slot -> geometric slot name ("UF", "UFR", "U") — the field
 * a non-JS reader joins on. On a big cube several slots share a name (the two
 * wings of one edge); that is the geometry, not a collision.
 */
export const PIECE_NAMES: Record<string, Record<string, readonly string[]>> = Object.fromEntries(
  Object.entries(RAW.puzzles).map(([puzzle, geo]) => [puzzle, geo.pieceNames]),
);

/** Puzzle -> orbit -> what its pieces are. `stickering.ts` narrows on this. */
export const ORBIT_KINDS: Record<string, Record<string, OrbitKind>> = Object.fromEntries(
  Object.entries(RAW.puzzles).map(([puzzle, geo]) => [puzzle, geo.orbitKinds]),
);

/**
 * Ladders that carry masks. Every ladder does now — the big-cube ones used to
 * be ordering only, which is why all 63 4x4/5x5 cases shipped with no
 * stickering attribute at all.
 */
export const RENDERED_LADDERS = RAW.renderedLadders as readonly LadderKey[];

/** The ladder assumed when nothing else says otherwise (e.g. /reference). */
export const DEFAULT_LADDER = RAW.defaultLadder as LadderKey;

/**
 * A case's stage, from its `group` — which is already exactly the right
 * granularity, and which all 185 cases carry. Throws rather than guessing: an
 * unmapped group is a data change that must be decided, not defaulted.
 */
export function stageOfGroup(group: string): StageKey {
  for (const rule of RAW.stageOfGroup) {
    const hit = rule.kind === "exact" ? group === rule.key : group.startsWith(rule.key);
    if (hit) return rule.stage as StageKey;
  }
  throw new Error(`ladders: no stage for group "${group}" — add a rule to gen-stickering.mjs`);
}

/**
 * A case's ladder, from its `phase`. `phase` is an opaque grouping tag on
 * CaseDef, NOT a key into src/data/phases.ts — generated cases carry
 * "full-f2l"/"full-oll"/"full-pll", which are not phases — so it is only ever
 * used as a lookup key here and never resolved to a display name.
 */
export function ladderOfPhase(phase: string): LadderKey {
  return (RAW.ladderOfPhase[phase] ?? DEFAULT_LADDER) as LadderKey;
}

/**
 * The default context for a case with no lesson around it — /reference and
 * /case/[...id]. Not a gap: the case's own `group` supplies the stage and its
 * `phase` supplies the ladder. A lesson that teaches a step in a different
 * order (align-edges is the one that does) passes an explicit context instead.
 */
export function contextForCase(def: { group: string; phase: string }): StageContext {
  return { ladder: ladderOfPhase(def.phase), stage: stageOfGroup(def.group) };
}

/** The puzzle a context is about. Its mask is in that puzzle's orbit space. */
export function puzzleOfContext(ctx: StageContext): string {
  const puzzle = LADDER_PUZZLE[ctx.ladder];
  if (!puzzle) throw new Error(`ladders: unknown ladder "${ctx.ladder}"`);
  return puzzle;
}

/** A stage's piece set on one puzzle, or null where the stage does not exist. */
export function stagePieces(
  stage: StageKey,
  puzzle: string,
): Record<string, number[]> | null | undefined {
  return STAGES[stage].pieces[puzzle];
}

/**
 * A stage's position on a ladder. A composite stage (f2l = f1l+e-layer,
 * oll = eo+oc, pll = cp+ep) is not listed on any ladder; it resolves to the
 * earliest position of its members, which is where the merged step happens.
 */
export function positionOf(stage: StageKey, ladder: LadderKey): number {
  const order = LADDERS[ladder];
  const direct = order.indexOf(stage);
  if (direct !== -1) return direct;
  const members = STAGES[stage].members ?? [];
  const positions = members.map((m) => order.indexOf(m as StageKey));
  if (positions.length === 0 || positions.some((i) => i === -1)) {
    throw new Error(`ladders: stage "${stage}" is not on ladder "${ladder}"`);
  }
  return Math.min(...positions);
}

/** The stages strictly before `stage` on `ladder` — exactly the DIM tier's source. */
export function priorStages(ctx: StageContext): readonly StageKey[] {
  return LADDERS[ctx.ladder].slice(0, positionOf(ctx.stage, ctx.ladder));
}

/**
 * The stage's mask in HOME-SLOT order, "ORBIT:chars,...", or undefined when the
 * ladder carries no mask for that stage. Remap through the ladder's puzzle
 * frame to get the player attribute — see stickering.ts.
 */
export function stageMask(ctx: StageContext): string | undefined {
  return RAW.masks[ctx.ladder]?.[ctx.stage];
}

/* ── The measured palettes, so the LIMITATION block above is checkable ────── */

/** A face colour as the player paints it in the highlight and dim tiers. */
export interface TierColours {
  highlight: string;
  dim: string;
}

/**
 * cubing.js's 3x3 renderer, sampled from decoded screenshots of the player.
 * There is no API that reports these; they are what the pixels are.
 */
export const PLAYER_PALETTE: Record<string, TierColours> = {
  white: { highlight: "#FFFFFF", dim: "#DDDDDD" },
  yellow: { highlight: "#FFFF00", dim: "#888800" },
  red: { highlight: "#FF0000", dim: "#660000" },
  green: { highlight: "#00FF00", dim: "#008800" },
  orange: { highlight: "#FF8800", dim: "#885500" },
  blue: { highlight: "#2266FF", dim: "#113388" },
};

/** The 3x3 renderer's "not yet reached" tier. */
export const PLAYER_GREY = "#666666";

/** PG3D, the 4x4/5x5 renderer: a different palette, not a resized one. */
export const BIG_CUBE_PALETTE: Record<string, TierColours> = {
  yellow: { highlight: "#F4F400", dim: "#B3B300" },
  green: { highlight: "#44EE00", dim: "#2FAF00" },
  red: { highlight: "#FF0000", dim: "#BC0000" },
};

/** PG3D's grey — lighter than the 3x3 renderer's, which is why it separates better. */
export const BIG_CUBE_GREY = "#444444";

/** Which two tiers a ratio is between. */
export type TierPair = "H:D" | "D:grey" | "H:grey";

/**
 * Every tier pair on the 3x3 renderer whose WCAG contrast is under 2:1, worst
 * first — the transcription of the LIMITATION block above, in a form a test can
 * recompute. The list is exhaustive at that threshold, and asserted to be:
 * a pair that drops below 2:1 and is missing here fails tests/algs.spec.ts.
 */
export const LOW_CONTRAST_PAIRS: readonly { face: string; pair: TierPair; ratio: number }[] = [
  { face: "orange", pair: "D:grey", ratio: 1.09 },
  { face: "blue", pair: "H:grey", ratio: 1.21 },
  { face: "green", pair: "D:grey", ratio: 1.24 },
  { face: "white", pair: "H:D", ratio: 1.36 },
  { face: "red", pair: "H:grey", ratio: 1.44 },
  { face: "yellow", pair: "D:grey", ratio: 1.52 },
  { face: "blue", pair: "D:grey", ratio: 1.97 },
];

/** WCAG 2.x relative luminance of a `#rrggbb` string. */
export function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const linear = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * linear[0]! + 0.7152 * linear[1]! + 0.0722 * linear[2]!;
}

/** WCAG contrast ratio between two `#rrggbb` strings, 1:1 to 21:1. */
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}
