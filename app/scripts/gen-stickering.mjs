/**
 * Derive the twisty-player stickering masks from cubing.js itself and write
 * them into the generated region of src/lib/stickering.ts, plus the progressive
 * stage ladder into src/data/extracted/stages.json.
 *
 * Why this exists: cubing.js hard-codes its cube palette per axis (U white,
 * F green, R red) and exposes no colour-scheme API, so the only way to get the
 * Cubepath scheme (yellow up, red front, green right) on screen is the setup
 * rotation `x2 y`. That rotation silently inverts every built-in
 * `experimental-stickering` value, because a stickering mask binds to the
 * CUBIE, not to the slot — with `x2 y` the stock OLL mask lands on the bottom
 * layer. So we stop passing `experimental-stickering` and emit our own
 * `experimental-stickering-mask-orbits` string instead, remapped through the
 * setup permutation. Those strings are derived here, never typed by hand.
 *
 * Usage: node scripts/gen-stickering.mjs  (npm run gen:stickering)
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * SCHEMA — src/data/extracted/stages.json  ("cubepath/stages@2")
 * ─────────────────────────────────────────────────────────────────────────────
 * This file is a CROSS-LANGUAGE CONTRACT. The app reads it through
 * src/lib/ladders.ts; the Python diagram pipeline (tools/cubepath) is intended
 * to read the same file so that one ladder drives both renderers. This repo has
 * shipped an ungated generated artifact before and paid for it, so: every field
 * below is documented here, and app/tests/algs.spec.ts re-derives the whole file
 * from cubing.js and fails if the committed copy drifts. Regenerate, never edit.
 *
 *   schema        "cubepath/stages@2". Bump on any breaking field change.
 *                 Version 2 made every per-puzzle field a map keyed by puzzle:
 *                 4x4x4 and 5x5x5 carry frames, orbits and piece sets of
 *                 their own, so the big-cube ladders render instead of falling
 *                 back to an unmasked cube.
 *   generatedBy   path of this script, for the reader who finds the file first.
 *   setupAlg      the whole-cube rotation the player applies ("x2 y"). Every
 *                 index below is in HOME-SLOT (pre-rotation) space; see `masks`.
 *   puzzles       puzzle -> {
 *                   orbits      [{name, numPieces}] in cubing.js's own order
 *                   orbitKinds  orbit -> "corner" | "edge" | "center", DERIVED
 *                               from how many faces move the orbit's pieces (3,
 *                               2, 1). This is what makes one recipe work on
 *                               every puzzle: a 4x4 wing and a 3x3 edge are
 *                               both "edge", and neither is named by index.
 *                   frame       orbit -> slot -> cubie under `setupAlg`, i.e.
 *                               the permutation a mask must be remapped through
 *                               before it reaches the player. Read off the
 *                               setup TRANSFORMATION, not off a pattern: big
 *                               cubes label interchangeable centres with the
 *                               face colour, so a pattern's `pieces` array is
 *                               not a permutation there and cannot be a frame.
 *                   pieceNames  orbit -> slot -> geometric slot name ("UF",
 *                               "UFR", "U"), DERIVED by asking which faces move
 *                               each piece. Names are geometry, not colour:
 *                               slot "DF" is the down-front slot, which under
 *                               `setupAlg` renders white-red in the Cubepath
 *                               scheme. This is the field a non-JS consumer
 *                               should join on — raw slot indices are
 *                               meaningless outside cubing.js's orbit ordering.
 *                               On a big cube several slots share a name (the
 *                               two wings of one edge); that is the geometry,
 *                               not a bug.
 *   baseMasks     stickering name -> cubing.js's own stock mask, HOME-SLOT
 *                 order. 3x3 semantics only — these are the `Stickering` union
 *                 in src/data/algs.ts, and they are the two-tier fallback used
 *                 when a caller passes no stage context.
 *   tierChars     tier -> aspect -> the serialized stickering-mask char.
 *                 tiers: highlight (what this stage solves), dim (solved by an
 *                 earlier stage, must be preserved), grey (not yet reached).
 *                 aspects: both | orientation | permutation.
 *   stages        stage key -> {
 *                   aspect    which of the piece's two properties this stage settles
 *                   puzzles   the puzzles this stage has a derived piece set for
 *                   members   null for a primitive stage; the primitive stage
 *                             keys it is the union of, for a composite one
 *                             (f2l = f1l+e-layer, oll = eo+oc, pll = cp+ep)
 *                   pieces    puzzle -> orbit -> slot indices
 *                   pieceNames  the same sets, as names from `puzzles[p].pieceNames`
 *                 }
 *   ladders       ladder key -> ordered stage keys. THE ONLY HAND-WRITTEN DATA
 *                 in this file. A composite stage is not listed; it resolves to
 *                 the earliest ladder position of any of its members.
 *   ladderPuzzle  ladder key -> the puzzle it is a ladder for.
 *   stageOfGroup  ordered match rules [{kind: "exact"|"prefix", key, stage}].
 *                 First match wins; a case's `group` picks its stage.
 *   ladderOfPhase phase key -> ladder key, plus `defaultLadder` for anything
 *                 unlisted. `phase` is an opaque grouping tag on CaseDef, NOT a
 *                 key into src/data/phases.ts (generated cases carry
 *                 "full-f2l"/"full-oll"/"full-pll", which are not phases), so it
 *                 is only ever used as a lookup key here, never resolved to a name.
 *   masks         ladder -> stage -> mask string in HOME-SLOT order,
 *                 "ORBIT:chars,ORBIT:chars,...". To get the value the player's
 *                 `experimental-stickering-mask-orbits` attribute takes, remap
 *                 slot -> cubie through the ladder's puzzle frame (FRAMES in
 *                 src/lib/stickering.ts), exactly as `baseMasks` is remapped.
 *   notes         free text for a human; not consumed by code.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { format, resolveConfig } from "prettier";

import { cube3x3x3, puzzles } from "cubing/puzzles";

/**
 * Maps cubing.js's default palette to U=yellow, L=blue, F=red, R=green,
 * B=orange, D=white — the Cubepath scheme in CLAUDE.md. `y x2` is NOT the
 * same rotation (it gives F=orange, R=blue); `y' x2` and `z2 y'` are.
 * tests/algs.spec.ts pins this against the palette, so it cannot silently rot.
 */
const SETUP_ALG = "x2 y";

/** Every value of the `Puzzle` union in src/data/algs.ts. */
const PUZZLES = ["3x3x3", "4x4x4", "5x5x5"];

/** Every value of the `Stickering` union in src/data/algs.ts. */
const STICKERINGS = ["full", "Cross", "F2L", "LL", "OLL", "OCLL", "PLL", "ELL"];

/**
 * `parseSerializedStickeringMask`'s char map, inverted: a piece's five facelet
 * masks identify the char that reproduces it. Read out of the installed
 * bundle (chunk-VRTKWZPL.js `pieceStickerings` + `charMap`); a piece whose
 * facelets match no char has no serialized form and fails the build.
 */
const CHAR_BY_FACELETS = new Map(
  Object.entries({
    "-": "regular,regular,regular,regular,regular",
    D: "dim,dim,dim,dim,dim",
    I: "ignored,ignored,ignored,ignored,ignored",
    X: "invisible,invisible,invisible,invisible,invisible",
    O: "regular,ignored,ignored,ignored,ignored",
    P: "dim,regular,regular,regular,regular",
    o: "dim,ignored,ignored,ignored,ignored",
    "?": "oriented,ignored,ignored,ignored,ignored",
    M: "mystery,mystery,mystery,mystery,mystery",
  }).map(([char, facelets]) => [facelets, char]),
);

/** @param {{ facelets: (string | { mask: string } | null)[] }} piece */
const faceletKey = (piece) =>
  // A null facelet has no serialized char; "null" fails the lookup below with
  // a message naming the orbit, rather than throwing on property access.
  piece.facelets.map((f) => (f === null ? "null" : typeof f === "string" ? f : f.mask)).join(",");

// ─────────────────────────────────────────────────────────────────────────────
// Per-puzzle geometry, all of it derived from cubing.js
// ─────────────────────────────────────────────────────────────────────────────

const FACES = ["U", "D", "F", "B", "R", "L"];
/**
 * slot-name length -> piece kind. A piece is named for the faces that move it.
 * @type {Record<number, string | undefined>}
 */
const KIND_BY_FACE_COUNT = { 1: "center", 2: "edge", 3: "corner" };

/**
 * @typedef {object} PuzzleGeometry
 * @property {import("cubing/kpuzzle").KPuzzle} kpuzzle
 * @property {{ orbitName: string, numPieces: number }[]} orbits
 * @property {Record<string, string>} orbitKinds
 * @property {Record<string, string[]>} pieceNames
 * @property {Record<string, number[]>} frame
 * @property {Record<string, Record<string, boolean[]>>} movedByFace
 */

/** @type {Record<string, PuzzleGeometry>} */
const GEO = {};

for (const puzzle of PUZZLES) {
  const kpuzzle = await puzzles[puzzle].kpuzzle();
  const orbits = kpuzzle.definition.orbits;

  /** Pieces an alg moves (permutation or orientation), per orbit, in slot order.
   * @param {string} alg @returns {Record<string, boolean[]>} */
  const movedBy = (alg) => {
    const t = kpuzzle.algToTransformation(alg);
    return Object.fromEntries(
      orbits.map((orbit) => {
        const d = t.transformationData[orbit.orbitName];
        return [
          orbit.orbitName,
          d.permutation.map((p, i) => p !== i || d.orientationDelta[i] !== 0),
        ];
      }),
    );
  };
  const movedByFace = Object.fromEntries(FACES.map((f) => [f, movedBy(f)]));

  // Geometric slot names, derived: a piece is named for the faces that move it
  // (an edge by 2, a corner by 3, a centre by 1), in the fixed order U D F B R L.
  const pieceNames = Object.fromEntries(
    orbits.map((orbit) => [
      orbit.orbitName,
      Array.from({ length: orbit.numPieces }, (_, slot) =>
        FACES.filter((f) => movedByFace[f][orbit.orbitName][slot]).join(""),
      ),
    ]),
  );

  // The kind of an orbit is how many faces move its pieces — and every piece in
  // one orbit must agree, or the derivation below has no meaning.
  /** @type {Record<string, string>} */
  const orbitKinds = {};
  for (const orbit of orbits) {
    const counts = new Set(pieceNames[orbit.orbitName].map((n) => n.length));
    if (counts.size !== 1) {
      throw new Error(
        `${puzzle}/${orbit.orbitName}: pieces sit on ${[...counts].join("/")} faces, not one count`,
      );
    }
    const kind = KIND_BY_FACE_COUNT[[...counts][0]];
    if (!kind) {
      throw new Error(
        `${puzzle}/${orbit.orbitName}: ${[...counts][0]} faces is no known piece kind`,
      );
    }
    orbitKinds[orbit.orbitName] = kind;
  }

  // Slot -> cubie under the setup rotation. A mask entry follows the physical
  // cubie, so the char meant for slot s must be written at index frame[s].
  // Read off the TRANSFORMATION, not off `defaultPattern().applyAlg(...)`:
  // big cubes label interchangeable centres by face colour, so a pattern's
  // `pieces` array is not a permutation there and would corrupt the remap.
  const setup = kpuzzle.algToTransformation(SETUP_ALG);
  const frame = Object.fromEntries(
    orbits.map((orbit) => {
      const perm = [...setup.transformationData[orbit.orbitName].permutation];
      if (new Set(perm).size !== perm.length) {
        throw new Error(
          `${puzzle}/${orbit.orbitName}: the ${SETUP_ALG} frame is not a permutation`,
        );
      }
      return [orbit.orbitName, perm];
    }),
  );

  GEO[puzzle] = { kpuzzle, orbits, orbitKinds, pieceNames, frame, movedByFace };
}

const ORBITS = GEO["3x3x3"].orbits;

/**
 * Serialize a stickering mask in HOME-SLOT order (no setup remap yet).
 * @param {string} name
 * @param {Awaited<ReturnType<typeof cube3x3x3.stickeringMask>>} mask
 */
function serialize(name, mask) {
  return ORBITS.map((orbit) => {
    const pieces = mask.orbits[orbit.orbitName]?.pieces ?? [];
    const chars = Array.from({ length: orbit.numPieces }, (_, i) => {
      const key = faceletKey(pieces[i] ?? { facelets: [] });
      const char = CHAR_BY_FACELETS.get(key);
      if (!char) {
        throw new Error(`${name}/${orbit.orbitName}[${i}]: no serialized char for "${key}"`);
      }
      return char;
    }).join("");
    return `${orbit.orbitName}:${chars}`;
  }).join(",");
}

/** @type {Record<string, string>} */
const baseMasks = {};
for (const name of STICKERINGS) {
  baseMasks[name] = serialize(name, await cube3x3x3.stickeringMask(name));
}

const lines = [
  `export const SETUP_ALG = ${JSON.stringify(SETUP_ALG)};`,
  "",
  "/** Stickering -> per-piece mask chars in HOME-SLOT order, one orbit per segment. */",
  "export const BASE_MASKS: Record<Stickering, string> = {",
  ...STICKERINGS.map((n) => `  ${JSON.stringify(n)}: ${JSON.stringify(baseMasks[n])},`),
  "};",
  "",
  "/** Puzzle -> orbit -> slot -> cubie under SETUP_ALG. Masks bind to the cubie. */",
  "export const FRAMES: Record<Puzzle, Record<string, readonly number[]>> = {",
  ...PUZZLES.flatMap((p) => [
    `  ${JSON.stringify(p)}: {`,
    ...Object.entries(GEO[p].frame).map(
      ([o, perm]) => `    ${JSON.stringify(o)}: [${perm.join(", ")}],`,
    ),
    "  },",
  ]),
  "};",
];

/**
 * `text` as the repo's own prettier config would write it to `url`.
 *
 * @param {string} text
 * @param {URL} url
 * @returns {Promise<string>}
 */
async function formatted(text, url) {
  const path = fileURLToPath(url);
  return format(text, { ...(await resolveConfig(path)), filepath: path });
}

/**
 * `--check` compares instead of writing, and exits 1 on any difference.
 *
 * Both outputs of this script are COMMITTED and read by the app at build time,
 * and until this flag existed nothing re-ran the generator to confirm the
 * committed copies still matched it. Every other generated artifact in the repo
 * is pinned that way (see CLAUDE.md's table); these two were the exception, so
 * hand-editing `stages.json` with a different stage value passed `make check`,
 * shipped, and was silently reverted by the next `npm run gen:stickering`. A
 * wrong stage is not cosmetic: it decides which pieces a diagram tells a
 * learner to preserve rather than solve.
 */
const CHECK = process.argv.includes("--check");
/** @type {string[]} */
const stale = [];

/**
 * @param {URL} url
 * @param {string} text  already prettier-formatted
 */
async function emit(url, text) {
  const path = fileURLToPath(url);
  if (!CHECK) {
    await writeFile(url, text);
    return;
  }
  const onDisk = await readFile(url, "utf8").catch(() => null);
  if (onDisk !== text) stale.push(path);
}

const target = new URL("../src/lib/stickering.ts", import.meta.url);
const START = "// <generated by scripts/gen-stickering.mjs — do not edit by hand>";
const END = "// </generated>";
const current = await readFile(target, "utf8");
const from = current.indexOf(START);
const to = current.indexOf(END);
if (from === -1 || to === -1) {
  throw new Error(`src/lib/stickering.ts is missing the ${START} / ${END} markers`);
}
const next = current.slice(0, from) + START + "\n" + lines.join("\n") + "\n" + current.slice(to);
// Emit what `prettier --write` would leave behind, not what is convenient to
// build: a 24-entry frame array is one long line here and a wrapped block
// there, so writing it raw left the repo failing its own `format:check` the
// moment anyone regenerated. The generator owns the region; it owns its shape.
await emit(target, await formatted(next, target));

console.log(
  `wrote ${STICKERINGS.length} masks + ${PUZZLES.length} frames to src/lib/stickering.ts`,
);
for (const n of STICKERINGS) console.log(`  ${n.padEnd(5)} ${baseMasks[n]}`);

// ─────────────────────────────────────────────────────────────────────────────
// The progressive stage ladder — src/data/extracted/stages.json
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The three tiers the user asked for, crossed with the aspect the stage settles.
 *
 *              both        orientation   permutation
 *   HIGHLIGHT  `-`         `O`           `P`
 *   DIM        `D`         `o`           `D`
 *   GREY       `I`         `I`           `I`
 *
 * `?` (teal) and `M` (pink) are deliberately unused: both introduce a hue that
 * is not on a cube and would read as a fourth semantic. The DIM row is exactly
 * `QUIET` in src/lib/stickering.ts — the demotion that already ships — and
 * tests/algs.spec.ts asserts the two agree rather than trusting this comment.
 * @type {Record<"highlight"|"dim"|"grey", Record<Aspect, string>>}
 */
const TIER_CHARS = {
  highlight: { both: "-", orientation: "O", permutation: "P" },
  dim: { both: "D", orientation: "o", permutation: "D" },
  grey: { both: "I", orientation: "I", permutation: "I" },
};

/** @typedef {"both" | "orientation" | "permutation"} Aspect */
/**
 * @typedef {object} StageSpec
 * @property {Aspect} aspect
 * @property {string[]} puzzles Puzzles the stage exists on.
 * @property {{ kind: "corner" | "edge" | "center", moved?: string[], still?: string[] }[]} [recipe]
 *   Derivation, in layer-move algebra: pieces of every orbit of that KIND moved
 *   by each move in `moved` and by none in `still`. No slot index is ever typed,
 *   and naming the kind rather than an orbit is what makes one recipe work on
 *   3x3, 4x4 and 5x5 alike — a 4x4 wing and a 3x3 edge are both "edge".
 * @property {string[]} [members] Composite stage: the union of these stages.
 */

/** The 3x3 stages, which every ladder passes through — big cubes reduce to them. */
const ON_EVERY_PUZZLE = PUZZLES;

/**
 * Stage definitions. The piece sets are DERIVED from layer moves; the only
 * hand-written things here are the aspect and which piece kind/layer a stage is
 * about.
 * @type {Record<string, StageSpec>}
 */
const STAGE_SPECS = {
  "cross": {
    aspect: "both",
    puzzles: ON_EVERY_PUZZLE,
    recipe: [{ kind: "edge", moved: ["D"] }, { kind: "center" }],
  },
  "f1l": {
    aspect: "both",
    puzzles: ON_EVERY_PUZZLE,
    recipe: [{ kind: "corner", moved: ["D"] }],
  },
  "e-layer": {
    aspect: "both",
    puzzles: ON_EVERY_PUZZLE,
    recipe: [{ kind: "edge", still: ["U", "D"] }],
  },
  "eo": {
    aspect: "orientation",
    puzzles: ON_EVERY_PUZZLE,
    recipe: [{ kind: "edge", moved: ["U"] }],
  },
  "oc": {
    aspect: "orientation",
    puzzles: ON_EVERY_PUZZLE,
    recipe: [{ kind: "corner", moved: ["U"] }],
  },
  "cp": {
    aspect: "permutation",
    puzzles: ON_EVERY_PUZZLE,
    recipe: [{ kind: "corner", moved: ["U"] }],
  },
  "ep": {
    aspect: "permutation",
    puzzles: ON_EVERY_PUZZLE,
    recipe: [{ kind: "edge", moved: ["U"] }],
  },
  "f2l": { aspect: "both", puzzles: ON_EVERY_PUZZLE, members: ["f1l", "e-layer"] },
  "oll": { aspect: "orientation", puzzles: ON_EVERY_PUZZLE, members: ["eo", "oc"] },
  "pll": { aspect: "permutation", puzzles: ON_EVERY_PUZZLE, members: ["cp", "ep"] },
  // Big-cube reduction: solve the centres, then pair the edge groups, and the
  // puzzle becomes a 3x3 in the stages above. Both sets are whole orbits, so
  // both are derived by kind with no layer condition at all.
  "444-centers": { aspect: "both", puzzles: ["4x4x4"], recipe: [{ kind: "center" }] },
  "444-pairing": { aspect: "both", puzzles: ["4x4x4"], recipe: [{ kind: "edge" }] },
  "555-centers": { aspect: "both", puzzles: ["5x5x5"], recipe: [{ kind: "center" }] },
  "555-pairing": { aspect: "both", puzzles: ["5x5x5"], recipe: [{ kind: "edge" }] },
};

/**
 * THE ORDERINGS — the one piece of hand-written data in the whole pipeline.
 *
 * There are two 3x3 ladders, not one, and they disagree about the last layer:
 * the beginner method permutes the yellow edges (ep) and positions the corners
 * (cp) BEFORE orienting them (oc), while CFOP orients first. The same algorithm
 * therefore sits at different stages in the two — Sune is the highlight of `oc`
 * on the CFOP ladder and appears inside the `ep` step on the beginner one — so
 * the tier assignment cannot live on CaseDef. The stage comes from the case's
 * `group`; the ladder comes from the calling context.
 * @type {Record<string, string[]>}
 */
const LADDERS = {
  beginner: ["cross", "f1l", "e-layer", "eo", "ep", "cp", "oc"],
  cfop: ["cross", "f1l", "e-layer", "eo", "oc", "cp", "ep"],
  "444": ["444-centers", "444-pairing", "cross", "f1l", "e-layer", "eo", "oc", "cp", "ep"],
  "555": ["555-centers", "555-pairing", "cross", "f1l", "e-layer", "eo", "oc", "cp", "ep"],
};

/** Ladder -> the puzzle it is a ladder for. Its stages must all exist there.
 * @type {Record<string, string>} */
const LADDER_PUZZLE = {
  beginner: "3x3x3",
  cfop: "3x3x3",
  "444": "4x4x4",
  "555": "5x5x5",
};

/**
 * Every ladder is rendered. This used to be a subset — the big-cube ladders
 * carried ordering but no masks, which is exactly why all 63 4x4/5x5 cases
 * shipped with no stickering attribute at all.
 */
const RENDERED_LADDERS = Object.keys(LADDERS);

/**
 * `CaseDef.group` -> stage. First match wins, so exact keys precede prefixes.
 * `group` is already the right granularity: all 194 cases carry one.
 * @type {{ kind: "exact" | "prefix", key: string, stage: string }[]}
 */
const STAGE_OF_GROUP = [
  { kind: "exact", key: "cross-eo", stage: "eo" },
  { kind: "exact", key: "2look-oll-corners", stage: "oc" },
  { kind: "exact", key: "2look-pll-corners", stage: "cp" },
  { kind: "exact", key: "2look-pll-edges", stage: "ep" },
  { kind: "exact", key: "444-parity", stage: "eo" },
  { kind: "exact", key: "555-parity", stage: "555-pairing" },
  // The beginner method's own algorithms, one group per step the reader meets
  // them at — the stage is where the reader MEETS the algorithm, which is what
  // the tier model is about. Righty and lefty are introduced to place the
  // first-layer corners (`f1l`) and reused at every later step; the two inserts
  // fill the middle layer (`e-layer`); Sune + U aligns the yellow edges (`ep`,
  // which on the beginner ladder comes BEFORE the corners — the corners it
  // scrambles are grey, exactly as the lesson says to treat them); Niklas
  // positions the last-layer corners (`cp`, again before orientation, which is
  // exactly the case the two-ladder split exists for); the Speed Tricks
  // finishers twist them (`oc`, the beginner ladder's last stage).
  { kind: "exact", key: "beginner-triggers", stage: "f1l" },
  { kind: "exact", key: "beginner-edge-insert", stage: "e-layer" },
  { kind: "exact", key: "beginner-edge-swap", stage: "ep" },
  { kind: "exact", key: "beginner-corner-cycle", stage: "cp" },
  { kind: "exact", key: "beginner-corner-twist", stage: "oc" },
  { kind: "exact", key: "bigcube-pairing", stage: "444-pairing" },
  { kind: "prefix", key: "f2l-", stage: "f2l" },
  { kind: "prefix", key: "oll-", stage: "oll" },
  { kind: "prefix", key: "pll-", stage: "pll" },
  { kind: "prefix", key: "4x4oll-", stage: "eo" },
  { kind: "prefix", key: "4x4pll-edges", stage: "ep" },
  { kind: "prefix", key: "4x4pll-", stage: "cp" },
];

/**
 * `CaseDef.phase` -> ladder. `phase` is an opaque tag, NOT a key into
 * src/data/phases.ts (generated cases carry "full-f2l"/"full-oll"/"full-pll",
 * which are not phases), so it is used only as a lookup key here.
 * @type {Record<string, string>}
 */
const LADDER_OF_PHASE = {
  "basics": "beginner",
  "phase-1": "beginner",
  "phase-1.5": "beginner",
  "phase-2": "cfop",
  "phase-3": "cfop",
  "full-cfop": "cfop",
  "full-f2l": "cfop",
  "full-oll": "cfop",
  "full-pll": "cfop",
  "444": "444",
  "555": "555",
};
const DEFAULT_LADDER = "cfop";

/** @param {string} puzzle @returns {Record<string, boolean[]>} an empty piece set. */
const emptySet = (puzzle) =>
  Object.fromEntries(
    GEO[puzzle].orbits.map((o) => [o.orbitName, new Array(o.numPieces).fill(false)]),
  );

/** Resolve a stage's piece set on one puzzle, recursing through composite members.
 * @param {string} key @param {string} puzzle
 * @returns {Record<string, boolean[]> | null} */
function pieceSet(key, puzzle) {
  const spec = STAGE_SPECS[key];
  if (!spec) throw new Error(`unknown stage "${key}"`);
  if (!spec.puzzles.includes(puzzle)) return null;
  const { orbits, orbitKinds, movedByFace } = GEO[puzzle];
  if (spec.members) {
    const out = emptySet(puzzle);
    for (const member of spec.members) {
      const set = pieceSet(member, puzzle);
      if (!set) return null;
      if (STAGE_SPECS[member].aspect !== spec.aspect) {
        throw new Error(
          `composite stage "${key}" (${spec.aspect}) has member "${member}" (${STAGE_SPECS[member].aspect})`,
        );
      }
      for (const o of orbits) {
        for (let i = 0; i < o.numPieces; i++) {
          out[o.orbitName][i] ||= set[o.orbitName][i];
        }
      }
    }
    return out;
  }
  if (!spec.recipe) return null;
  const out = emptySet(puzzle);
  for (const { kind, moved = [], still = [] } of spec.recipe) {
    for (const o of orbits) {
      if (orbitKinds[o.orbitName] !== kind) continue;
      for (let i = 0; i < o.numPieces; i++) {
        out[o.orbitName][i] ||=
          moved.every((m) => movedByFace[m][o.orbitName][i]) &&
          still.every((m) => !movedByFace[m][o.orbitName][i]);
      }
    }
  }
  return out;
}

/** stage -> puzzle -> piece set (or null where the stage does not exist).
 * @type {Record<string, Record<string, Record<string, boolean[]> | null>>} */
const PIECE_SETS = Object.fromEntries(
  Object.keys(STAGE_SPECS).map((k) => [
    k,
    Object.fromEntries(PUZZLES.map((p) => [p, pieceSet(k, p)])),
  ]),
);

/**
 * A stage's position on a ladder. A composite stage is not listed on any
 * ladder; it resolves to the earliest position of any of its members, which is
 * exactly where the merged step happens (full OLL replaces the eo/oc pair).
 * @param {string} stage @param {string} ladder @returns {number}
 */
function positionOf(stage, ladder) {
  const order = LADDERS[ladder];
  if (!order) throw new Error(`unknown ladder "${ladder}"`);
  const direct = order.indexOf(stage);
  if (direct !== -1) return direct;
  const members = STAGE_SPECS[stage]?.members ?? [];
  const positions = members.map((m) => order.indexOf(m)).filter((i) => i !== -1);
  if (positions.length !== members.length || positions.length === 0) {
    throw new Error(`stage "${stage}" is not on ladder "${ladder}"`);
  }
  return Math.min(...positions);
}

/**
 * The progressive mask for one stage on one ladder, in HOME-SLOT order.
 *
 * Every edge and corner starts GREY. Each stage strictly before this one paints
 * its pieces DIM — later prior wins, so a piece that two earlier stages settled
 * carries the dim char of the LAST one that touched it (a last-layer edge that
 * has been both oriented and permuted reads `D` "solved", not `o` "orientation
 * settled"). Then this stage paints its own pieces HIGHLIGHT, overwriting.
 * HIGHLIGHT and DIM are therefore disjoint by construction.
 *
 * CENTRES ARE THE EXCEPTION, and it is a rule, not a special case: a centre is
 * fixed by definition — it is the frame every recognition cue on the site is
 * written against — so it is never GREY. Centres start DIM, and exactly one
 * stage per ladder highlights them: the first one whose recipe claims them
 * (`cross` on the 3x3 ladders, `444-centers`/`555-centers` on the big-cube
 * ones, where the centres really are the first thing you solve). Every later
 * stage leaves them dim rather than re-claiming them.
 * @param {string} ladder @param {string} stage @returns {string}
 */
function stageMask(ladder, stage) {
  const puzzle = LADDER_PUZZLE[ladder];
  const { orbits, orbitKinds } = GEO[puzzle];
  const at = positionOf(stage, ladder);
  const centreOwner = LADDERS[ladder].find((k) =>
    orbits.some(
      (o) =>
        orbitKinds[o.orbitName] === "center" &&
        (PIECE_SETS[k][puzzle]?.[o.orbitName] ?? []).some(Boolean),
    ),
  );
  const chars = Object.fromEntries(
    orbits.map((o) => [
      o.orbitName,
      new Array(o.numPieces).fill(
        orbitKinds[o.orbitName] === "center" ? TIER_CHARS.dim.both : TIER_CHARS.grey.both,
      ),
    ]),
  );
  /** @param {string} key @param {"dim"|"highlight"} tier */
  const paint = (key, tier) => {
    const set = PIECE_SETS[key][puzzle];
    if (!set) throw new Error(`stage "${key}" on ladder "${ladder}" has no ${puzzle} piece set`);
    const char = TIER_CHARS[tier][STAGE_SPECS[key].aspect];
    for (const o of orbits) {
      // Centres are owned by one stage per ladder and dim everywhere else.
      if (orbitKinds[o.orbitName] === "center" && key !== centreOwner) continue;
      for (let i = 0; i < o.numPieces; i++) if (set[o.orbitName][i]) chars[o.orbitName][i] = char;
    }
  };
  for (const key of LADDERS[ladder].slice(0, at)) paint(key, "dim");
  paint(stage, "highlight");
  return orbits.map((o) => `${o.orbitName}:${chars[o.orbitName].join("")}`).join(",");
}

/** Stages a ladder can render: the ones it lists, plus composites of them. */
const stagesOn = (/** @type {string} */ ladder) =>
  Object.keys(STAGE_SPECS).filter((k) => {
    try {
      positionOf(k, ladder);
      return PIECE_SETS[k][LADDER_PUZZLE[ladder]] !== null;
    } catch {
      return false;
    }
  });

/** @type {Record<string, Record<string, string>>} */
const masks = {};
for (const ladder of RENDERED_LADDERS) {
  masks[ladder] = Object.fromEntries(stagesOn(ladder).map((s) => [s, stageMask(ladder, s)]));
}

/** @param {Record<string, boolean[]> | null} set @param {string} puzzle */
const indicesOf = (set, puzzle) =>
  set === null
    ? null
    : Object.fromEntries(
        GEO[puzzle].orbits.map((o) => [
          o.orbitName,
          set[o.orbitName].flatMap((v, i) => (v ? [i] : [])),
        ]),
      );

/** @param {Record<string, number[]> | null} indices @param {string} puzzle */
const namesOf = (indices, puzzle) =>
  indices === null
    ? null
    : Object.fromEntries(
        Object.entries(indices).map(([o, list]) => [
          o,
          list.map((i) => GEO[puzzle].pieceNames[o][i]),
        ]),
      );

const stagesFile = {
  schema: "cubepath/stages@2",
  generatedBy: "app/scripts/gen-stickering.mjs",
  setupAlg: SETUP_ALG,
  puzzles: Object.fromEntries(
    PUZZLES.map((p) => [
      p,
      {
        orbits: GEO[p].orbits.map((o) => ({ name: o.orbitName, numPieces: o.numPieces })),
        orbitKinds: GEO[p].orbitKinds,
        frame: GEO[p].frame,
        pieceNames: GEO[p].pieceNames,
      },
    ]),
  ),
  baseMasks,
  tierChars: TIER_CHARS,
  stages: Object.fromEntries(
    Object.entries(STAGE_SPECS).map(([key, spec]) => {
      const pieces = Object.fromEntries(
        spec.puzzles.map((p) => [p, indicesOf(PIECE_SETS[key][p], p)]),
      );
      return [
        key,
        {
          aspect: spec.aspect,
          puzzles: spec.puzzles,
          members: spec.members ?? null,
          pieces,
          pieceNames: Object.fromEntries(spec.puzzles.map((p) => [p, namesOf(pieces[p], p)])),
        },
      ];
    }),
  ),
  ladders: LADDERS,
  ladderPuzzle: LADDER_PUZZLE,
  renderedLadders: RENDERED_LADDERS,
  stageOfGroup: STAGE_OF_GROUP,
  ladderOfPhase: LADDER_OF_PHASE,
  defaultLadder: DEFAULT_LADDER,
  masks,
  notes: [
    "Masks are in HOME-SLOT order; remap through the ladder's puzzle frame (puzzles[p].frame, mirrored as FRAMES in src/lib/stickering.ts) to get the player attribute.",
    "A centre is never GREY and is highlighted by exactly one stage per ladder — the first one that claims it. It is the frame every recognition cue is written against, so 'not yet reached' is never true of it.",
    "LIMITATION (3x3 renderer): the tiers are told apart by colour alone, and every pair under WCAG 2:1, worst first, is — grey is #666666, H highlight, D dim: 1.09:1 orange D #885500 vs grey; 1.21:1 blue H #2266FF vs grey; 1.24:1 green D #008800 vs grey; 1.36:1 white D #DDDDDD vs H #FFFFFF; 1.44:1 red H #FF0000 vs grey; 1.52:1 yellow D #888800 vs grey; 1.97:1 blue D #113388 vs grey. So both boundaries fail, on different faces: dim-vs-grey is the worst pair on the cube and the most common, highlight-vs-grey carries the most meaning and fails second-worst, and highlight-vs-dim fails only on white — which confines that clash to `f1l` and `f2l`. Every ratio measured off decoded screenshots of the player; src/lib/ladders.ts carries the palette as data and the tests recompute it.",
    "LIMITATION (big cubes): 4x4 and 5x5 render through PG3D, a different palette whose dim is a ~0.73 multiply and whose grey is #444444. Measured: yellow #F4F400/#B3B300 H:D 1.90:1, D:grey 4.34:1, H:grey 8.25:1; green #44EE00/#2FAF00 1.86:1, 3.36:1, 6.25:1; red #FF0000/#BC0000 1.67:1, 1.46:1, 2.44:1. The trade runs the other way there: highlight and dim are closer (all three faces under 2:1), but dim and grey are much further apart on every face except red, and highlight-vs-grey is the strongest boundary rather than the weakest.",
    "There is no cube-palette API in cubing 0.63.3, so none of this is tunable in the player. The worst-affected stages are illustrated by static SVGs, where the palette is ours; the tier assignment in this file is the shared artifact, the colours are not.",
  ],
};

const stagesPath = new URL("../src/data/extracted/stages.json", import.meta.url);
if (!CHECK) await mkdir(new URL("./", stagesPath), { recursive: true });
await emit(stagesPath, await formatted(JSON.stringify(stagesFile, null, 2), stagesPath));

console.log(`\nwrote ${Object.keys(STAGE_SPECS).length} stages to src/data/extracted/stages.json`);
for (const ladder of RENDERED_LADDERS) {
  console.log(`  ${ladder} (${LADDER_PUZZLE[ladder]}): ${LADDERS[ladder].join(" -> ")}`);
  for (const [stage, mask] of Object.entries(masks[ladder])) {
    console.log(`    ${stage.padEnd(12)} ${mask}`);
  }
}

if (CHECK) {
  if (stale.length) {
    console.error(
      `\nSTALE — these committed files no longer match this generator:\n` +
        stale.map((p) => `  ${p}`).join("\n") +
        `\n\nRun \`npm run gen:stickering\` and commit the result.\n`,
    );
    process.exit(1);
  }
  console.log("\nstages.json and stickering.ts match the generator");
}
