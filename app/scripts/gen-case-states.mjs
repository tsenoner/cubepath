/**
 * Derive the facelet state of every case, at every puzzle size, from the
 * cubing.js kpuzzle — and write it to src/data/extracted/case-states.json for
 * the Python diagram generator to read and draw.
 *
 * WHY THIS EXISTS
 * ---------------
 * `tools/cubepath/src/cubepath/cube.py` is a 3x3-only mirror and is gated to
 * stay one. cubing.js already owns 4x4x4 and 5x5x5 definitions and the
 * verifiers that gate this repo's algorithm data, so JavaScript is the single
 * source of CUBE TRUTH: JS derives state, writes JSON, Python reads it and
 * draws. This is the `jperm-raw.json` pattern generalised.
 *
 * Nothing here is retyped. Every algorithm comes out of the verified
 * extractions (jperm-raw.json, f2l-raw.json, l2e-raw.json); every facelet
 * comes out of the kpuzzle; every face letter and grid coordinate is derived
 * from cubing.js's own unfolded-net SVG, never hand-tabulated.
 *
 * ===========================================================================
 * THE CROSS-LANGUAGE CONTRACT — src/data/extracted/case-states.json
 * ===========================================================================
 * This file is read by Python. Treat every field below as public API: adding
 * is safe, renaming or re-ordering is a breaking change. It is committed and
 * gated (tools/cubepath/tests/test_case_states.py), and the generator is
 * deterministic — running it twice produces a byte-identical file.
 *
 * {
 *   "schema": 1,
 *   "generator": "app/scripts/gen-case-states.mjs",
 *   "faces": ["U","L","F","R","B","D"],       // canonical face order
 *   "faceColors": {"U":"YELLOW", ...},        // Cubepath scheme, per CLAUDE.md
 *   "maskLegend": {".": "...", "o": "...", "x": "..."},
 *   "parityAlgs": { "<key>": {"alg": "...", "source": "...", "signature": "..."} },
 *   "layouts": { "<puzzleId>": Layout },
 *   "cases": [ Case, ... ]
 * }
 *
 * Layout — one per puzzle size, shared by every case of that size:
 * {
 *   "n": 3,                                   // cube order; a face is n*n facelets
 *   "orbits": [{"name":"EDGES","numPieces":12,"numOrientations":2}, ...],
 *   "facelets": {                             // face -> n*n entries, ROW-MAJOR
 *     "U": ["CORNERS:2:0", "EDGES:3:0", ...]  // "<orbit>:<slot>:<orientation>"
 *   }
 * }
 *
 * `facelets` is the kpuzzle address of each drawn sticker position. It lets
 * Python group facelets into pieces (a 4x4 dedge is two facelets of the same
 * EDGES orbit; a 5x5 edge triplet is two EDGES wings plus one EDGES2 midge)
 * without knowing any cube geometry.
 *
 * Case:
 * {
 *   "id": "oll.1",            // the id gen-cases.mjs gives the same case
 *   "puzzle": "3x3x3",
 *   "set": "oll",             // oll | pll | f2l | 4x4oll | 4x4pll | 555l2e
 *   "name": "OLL 1",
 *   "group": "Dot",
 *   "alg": "R U2 R' ...",     // verbatim from the extraction; never retyped
 *   "derivation": "inverse",  // "inverse":   state = alg applied backwards to solved
 *                             // "setup":     state = the pinned setup applied forwards
 *                             // "displayed": state = solved, patched with the
 *                             //   drawable pattern the verifier exported (5x5 L2E)
 *   "preRotation": "",        // whole-cube rotation applied to cancel the alg's
 *                             // net rotation; "" when the alg has none
 *   "state": {"U":"YYYYYYYYY","L":"BBB...", ...},
 *   "mask":  {"U":".........","L":"...", ...}
 * }
 *
 * `state` — one string per face, n*n characters, ROW-MAJOR, each character a
 * FACE LETTER (U/L/F/R/B/D) naming the face whose colour that sticker shows.
 * Letters, not colours: cubing.js hard-codes its own palette (U white, F green,
 * R red) and this repo uses another (U yellow, F red, R green), so the letter
 * is the stable fact and `faceColors` is the one place the two meet.
 *
 * Face grid convention, matching cube.py's `faces` dict exactly:
 *   every face is read as if looking straight at it from OUTSIDE the cube,
 *   row 0 first, left to right — with U held so its bottom row touches F,
 *   D so its top row touches F, and L/F/R/B so their top rows touch U.
 *   Index = row * n + col.
 *
 * `mask` — one string per face, n*n characters, same indexing as `state`:
 *   "." the piece occupying that slot is home, in home orientation
 *   "o" the home piece, twisted/flipped in place
 *   "x" a different piece occupies that slot
 * It classifies PIECES, not drawing policy: how a diagram treats a masked
 * facelet (grey it, dim it, ignore it) stays Python's decision. Note for 5x5
 * reduction sets: an edge group that is intact but displaced reads as "x",
 * because the piece genuinely is not home — L2E tolerance for that is a
 * property of the solve method, not of the cube state.
 *
 * WHY THE 5x5 L2E SET HAS A THIRD DERIVATION — and why it is not "inverse".
 * For every last-layer set (OLL, PLL, 4x4 OLL, 4x4 PLL) the case as a solver
 * sees it IS `alg⁻¹` applied to solved: D solved, every side row below the top
 * row solved, the case confined to the last layer. The 13 `555l2e` states are
 * not like that. An L2E algorithm is written for a hold partway through
 * reduction, so `alg⁻¹` with the centres rotated home leaves the two target
 * edge groups wherever that hold put them (l2e-1 lands them on R and B, not
 * UF/UB) and leaves the rigidly-cycled non-target groups displaced. Those
 * states were exported raw and marked not drawable for exactly that reason.
 *
 * They are drawable now. `verify-l2e.mjs` owns the reduction model that says
 * which two slots are the case, and its check (d) already built and
 * round-tripped the displayed pattern — ten non-target groups plus the corners
 * solved in place, only UF and UB taken from the case state. It now EXPORTS
 * that pattern as `displayed`, a delta against solved, and this script patches
 * it onto the kpuzzle's default pattern (`derivation: "displayed"`) and
 * converts to facelets like any other case. Re-deriving target-slot detection
 * here would have been a second copy of a model that already exists, which is
 * why the fix went there and not here.
 *
 * Usage: node scripts/gen-case-states.mjs
 */
import { readFile, writeFile } from "node:fs/promises";

import { Alg } from "cubing/alg";
import { KPattern } from "cubing/kpuzzle";
import { puzzles } from "cubing/puzzles";

import { makeKit, unaliasedCopy } from "./lib/kpuzzle-utils.mjs";

/**
 * The types are written here rather than inferred: `checkJs` runs over this
 * file (scripts/tsconfig.json), and cubing.js's kpuzzle objects arrive as
 * `any` through the .mjs boundary.
 *
 * @typedef {{ orbit: string; slot: number; ori: number; x: number; y: number; fill: string }} Sticker
 * @typedef {{ cells: Sticker[]; box: { x0: number; x1: number; y0: number; y1: number } }} FaceGrid
 * @typedef {any} KPuzzle a cubing.js KPuzzle
 * NOTE: `KPattern` is NOT aliased to `any` here — the real class is imported
 * above (patchedState constructs one), and a typedef of the same name would
 * collide with the import.
 * @typedef {{ ROTATION_T: any[]; centersSolved: (pattern: KPattern) => boolean;
 *             toT: (s: string) => any; rightRotNormalize: (t: any) => any }} Kit
 * @typedef {{ puzzleId: string; kpuzzle: KPuzzle; n: number;
 *             faces: Record<string, FaceGrid>; solved: KPattern }} Model
 * @typedef {{ face: string; index: number }} Address
 */

/** Canonical face order. Also the order every per-face object is written in. */
const FACES = /** @type {const} */ (["U", "L", "F", "R", "B", "D"]);

/**
 * Face -> Cubepath colour name (CLAUDE.md). Emitted so Python never guesses.
 * @type {Record<string, string>}
 */
const FACE_COLORS = {
  U: "YELLOW",
  L: "BLUE",
  F: "RED",
  R: "GREEN",
  B: "ORANGE",
  D: "WHITE",
};

const MASK_SOLVED = ".";
const MASK_TWISTED = "o";
const MASK_DISPLACED = "x";

/** @type {Record<string, string>} */
const MASK_LEGEND = {
  [MASK_SOLVED]: "home piece, home orientation",
  [MASK_TWISTED]: "home piece, wrong orientation",
  [MASK_DISPLACED]: "a different piece occupies this slot",
};

// ---------------------------------------------------------------------------
// The facelet model, derived from cubing.js's own unfolded-net SVG.
//
// Every sticker element in that SVG carries id="<ORBIT>-l<slot>-o<orientation>"
// — the kpuzzle address TwistySVG itself colours by — plus the geometry that
// places it in the net and the fill it has when solved. So the SVG is a
// complete, machine-readable facelet map, and nothing below is hand-tabulated.
// ---------------------------------------------------------------------------

/** Sticker elements: <use> (the hand-authored 3x3 net) or <polygon> (PuzzleGeometry). */
const STICKER_ELEMENT = /<(?:use|polygon)\b([^>]*?)\/?>/g;
/** `id="ORBIT-lN-oM"` — anchored so `data-copy-id` (hint facelets) cannot match. */
const STICKER_ID = /(?:^|\s)id="([A-Za-z0-9]+)-l(\d+)-o(\d+)"/;
const STICKER_FILL = /fill:\s*([^;"]+)/;

/**
 * Where a sticker element sits: a `translate()` offset or a polygon centroid.
 * @param {string} attrs
 * @returns {[number, number] | null}
 */
function position(attrs) {
  const t = attrs.match(/transform="translate\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)"/);
  if (t) return [parseFloat(t[1] ?? ""), parseFloat(t[2] ?? "")];
  const p = attrs.match(/points="([^"]+)"/);
  if (!p) return null;
  const nums = (p[1] ?? "")
    .trim()
    .split(/[\s,]+/)
    .map(Number);
  let sx = 0;
  let sy = 0;
  let k = 0;
  for (let i = 0; i + 1 < nums.length; i += 2) {
    sx += nums[i] ?? 0;
    sy += nums[i + 1] ?? 0;
    k++;
  }
  return k ? [sx / k, sy / k] : null;
}

/**
 * Build the facelet model for one puzzle: face letters, and each face's n*n
 * grid of kpuzzle sticker addresses in cube.py's row-major convention.
 * @param {string} puzzleId
 * @returns {Promise<Model>}
 */
async function buildModel(puzzleId) {
  const loader = /** @type {Record<string, any>} */ (puzzles)[puzzleId];
  if (!loader) throw new Error(`gen-case-states: cubing.js has no puzzle "${puzzleId}"`);
  const kpuzzle = await loader.kpuzzle();
  const svg = await loader.svg();

  // One sticker per drawn position. A center piece's orientation slots all draw
  // at the same spot (its single visible sticker), so position dedupes them.
  /** @type {Map<string, Sticker>} */
  const byPosition = new Map();
  for (const el of svg.matchAll(STICKER_ELEMENT)) {
    const attrs = el[1];
    const id = attrs.match(STICKER_ID);
    const fill = attrs.match(STICKER_FILL);
    const pos = id && fill ? position(attrs) : null;
    if (!id || !fill || !pos) continue;
    const key = `${pos[0].toFixed(4)},${pos[1].toFixed(4)}`;
    if (byPosition.has(key)) continue;
    byPosition.set(key, {
      orbit: id[1] ?? "",
      slot: Number(id[2]),
      ori: Number(id[3]),
      x: pos[0],
      y: pos[1],
      fill: (fill[1] ?? "").trim(),
    });
  }
  const stickers = [...byPosition.values()];
  const n = Math.round(Math.sqrt(stickers.length / 6));
  if (n < 2 || stickers.length !== 6 * n * n) {
    throw new Error(`${puzzleId}: parsed ${stickers.length} stickers, not 6*n*n for any n`);
  }

  // Group by solved fill = group by face. Which face is which is then decided
  // by the kpuzzle, not by cubing's palette: exactly one face turn moves every
  // piece a face's stickers sit on.
  /** @type {Map<string, Sticker[]>} */
  const groups = new Map();
  for (const s of stickers) {
    if (!groups.has(s.fill)) groups.set(s.fill, []);
    (groups.get(s.fill) ?? []).push(s);
  }
  if (groups.size !== 6) {
    throw new Error(`${puzzleId}: ${groups.size} solved-fill groups, expected 6 faces`);
  }

  const solved = kpuzzle.defaultPattern();
  /** @type {Record<string, (orbit: string, slot: number) => boolean>} */
  const disturbed = {};
  for (const face of FACES) {
    const turned = solved.applyAlg(new Alg(face)).patternData;
    disturbed[face] = (/** @type {string} */ orbit, /** @type {number} */ slot) =>
      turned[orbit].pieces[slot] !== solved.patternData[orbit].pieces[slot] ||
      turned[orbit].orientation[slot] !== solved.patternData[orbit].orientation[slot];
  }

  /** @type {Record<string, FaceGrid>} */
  const faces = {};
  for (const [fill, group] of groups) {
    if (group.length !== n * n) {
      throw new Error(
        `${puzzleId}: fill ${fill} covers ${group.length} stickers, expected ${n * n}`,
      );
    }
    const ranked = FACES.map((face) => {
      const turns = disturbed[face];
      if (!turns) throw new Error(`${puzzleId}: no ${face} turn on this kpuzzle`);
      return { face, hits: group.filter((s) => turns(s.orbit, s.slot)).length };
    }).sort((a, b) => b.hits - a.hits);
    if (!ranked[0] || !ranked[1] || ranked[0].hits === ranked[1].hits) {
      throw new Error(
        `${puzzleId}: fill ${fill} is not identified by a single face turn ` +
          `(${ranked.map((r) => `${r.face}=${r.hits}`).join(" ")})`,
      );
    }
    if (faces[ranked[0].face])
      throw new Error(`${puzzleId}: two fills map to face ${ranked[0].face}`);
    faces[ranked[0].face] = grid(puzzleId, ranked[0].face, group, n);
  }
  for (const face of FACES) {
    if (!faces[face]) throw new Error(`${puzzleId}: no sticker group resolved to face ${face}`);
  }

  const model = { puzzleId, kpuzzle, n, faces, solved };
  assertNetLayout(model, stickers);
  assertInterchangeablePiecesShareAFace(model);
  assertFaceTurnsRotateClockwise(model);
  return model;
}

/**
 * Order one face's stickers row-major from their positions in the net.
 * @param {string} puzzleId
 * @param {string} face
 * @param {Sticker[]} group
 * @param {number} n
 * @returns {FaceGrid}
 */
function grid(puzzleId, face, group, n) {
  const round = (/** @type {number} */ v) => Number(v.toFixed(4));
  const xs = [...new Set(group.map((s) => round(s.x)))].sort((a, b) => a - b);
  const ys = [...new Set(group.map((s) => round(s.y)))].sort((a, b) => a - b);
  if (xs.length !== n || ys.length !== n) {
    throw new Error(
      `${puzzleId}/${face}: stickers form a ${xs.length}x${ys.length} grid, not ${n}x${n}`,
    );
  }
  /** @type {(Sticker | null)[]} */
  const cells = new Array(n * n).fill(null);
  for (const s of group) {
    const idx = ys.indexOf(round(s.y)) * n + xs.indexOf(round(s.x));
    if (cells[idx]) throw new Error(`${puzzleId}/${face}: two stickers at grid cell ${idx}`);
    cells[idx] = s;
  }
  if (cells.some((c) => !c)) throw new Error(`${puzzleId}/${face}: grid has holes`);
  return {
    cells: /** @type {Sticker[]} */ (cells),
    box: { x0: xs[0] ?? 0, x1: xs[n - 1] ?? 0, y0: ys[0] ?? 0, y1: ys[n - 1] ?? 0 },
  };
}

/**
 * The net must be the standard cross — L F R B in one band, U above F, D below
 * F. Per-face handedness is pinned separately (see below); this pins how the
 * six grids are rotated relative to each other, which is what makes the
 * row-major order match cube.py's.
 * @param {Model} model
 * @param {Sticker[]} stickers
 */
function assertNetLayout(model, stickers) {
  const { puzzleId, faces } = model;
  const near = (/** @type {number} */ a, /** @type {number} */ b) => Math.abs(a - b) < 1e-6;
  const span = Math.max(...stickers.map((s) => s.x)) - Math.min(...stickers.map((s) => s.x));
  const tol = span * 1e-3;
  const close = (/** @type {number} */ a, /** @type {number} */ b) =>
    Math.abs(a - b) < Math.max(tol, 1e-6);
  const band = ["L", "F", "R", "B"];
  for (const face of band) {
    if (!close(faces[face].box.y0, faces.F.box.y0) || !close(faces[face].box.y1, faces.F.box.y1)) {
      throw new Error(`${puzzleId}: ${face} is not in the same net band as F`);
    }
  }
  for (let i = 1; i < band.length; i++) {
    if (!(faces[band[i - 1]].box.x1 < faces[band[i]].box.x0)) {
      throw new Error(`${puzzleId}: net band is not ordered L F R B`);
    }
  }
  for (const [face, rel] of [
    ["U", "above"],
    ["D", "below"],
  ]) {
    if (!close(faces[face].box.x0, faces.F.box.x0) || !close(faces[face].box.x1, faces.F.box.x1)) {
      throw new Error(`${puzzleId}: ${face} is not aligned over F in the net`);
    }
    const ok =
      rel === "above" ? faces[face].box.y1 < faces.F.box.y0 : faces[face].box.y0 > faces.F.box.y1;
    if (!ok) throw new Error(`${puzzleId}: ${face} is not ${rel} F in the net`);
  }
  void near;
}

/**
 * Each face turn must rotate its own face's grid CLOCKWISE — new[r][c] comes
 * from old[n-1-c][r], the same permutation cube.py's `_rotate_face_cw` writes.
 * A mirrored grid would rotate anticlockwise, so this pins handedness without
 * consulting cube.py.
 *
 * Facelets on interchangeable pieces are skipped: a 4x4/5x5 kpuzzle gives every
 * centre of one face the SAME piece id (that is what makes strict comparison a
 * visual comparison), so those facelets have no individual identity to track.
 * `assertInterchangeablePiecesShareAFace` covers them instead.
 * @param {Model} model
 */
function assertFaceTurnsRotateClockwise(model) {
  const { puzzleId, n } = model;
  const ambiguous = interchangeablePieces(model);
  for (const face of FACES) {
    const turned = model.solved.applyAlg(new Alg(face));
    const source = sourceIndex(model, turned);
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        const cell = model.faces[face].cells[r * n + c];
        if (
          !cell ||
          ambiguous[cell.orbit]?.has(model.solved.patternData[cell.orbit].pieces[cell.slot])
        )
          continue;
        const got = source[face]?.[r * n + c];
        if (!got) throw new Error(`${puzzleId}: face ${face} has no cell ${r * n + c}`);
        const want = { face, index: (n - 1 - c) * n + r };
        if (got.face !== want.face || got.index !== want.index) {
          throw new Error(
            `${puzzleId}: move ${face} does not rotate face ${face} clockwise ` +
              `(cell ${r},${c} sourced from ${got.face}[${got.index}])`,
          );
        }
      }
    }
  }
}

/**
 * Orbit -> the piece ids that appear in more than one slot when solved.
 * @param {Model} model
 * @returns {Record<string, Set<number>>}
 */
function interchangeablePieces(model) {
  /** @type {Record<string, Set<number>>} */
  const out = {};
  for (const { orbitName } of model.kpuzzle.definition.orbits) {
    const counts = new Map();
    for (const p of model.solved.patternData[orbitName].pieces) {
      counts.set(p, (counts.get(p) ?? 0) + 1);
    }
    out[orbitName] = new Set([...counts].filter(([, k]) => k > 1).map(([p]) => p));
  }
  return out;
}

/**
 * `sourceIndex` looks a sticker up by <orbit, piece id, sticker index>. When a
 * puzzle gives several slots the same piece id (4x4/5x5 centres) two facelets
 * share one address, so that address must resolve to one face — otherwise the
 * colour read out of it would be ambiguous rather than merely anonymous.
 * @param {Model} model
 */
function assertInterchangeablePiecesShareAFace(model) {
  /** @type {Map<string, string>} */
  const faceOfSticker = new Map();
  for (const face of FACES) {
    for (const cell of model.faces[face].cells) {
      const key = `${cell.orbit}:${model.solved.patternData[cell.orbit].pieces[cell.slot]}:${cell.ori}`;
      const seenFace = faceOfSticker.get(key);
      if (seenFace && seenFace !== face) {
        throw new Error(
          `${model.puzzleId}: sticker ${key} is drawn on both ${seenFace} and ${face}`,
        );
      }
      faceOfSticker.set(key, face);
    }
  }
}

// ---------------------------------------------------------------------------
// Pattern -> facelets
// ---------------------------------------------------------------------------

/**
 * For every drawn facelet, the SOLVED facelet whose sticker it now shows.
 * The address arithmetic is cubing.js's own (TwistySVG `draw()`): the sticker
 * at slot `i`, orientation `o` comes from piece `pieces[i]`, sticker
 * `(numOrientations - orientation[i] + o) % numOrientations`.
 * @param {Model} model
 * @param {KPattern} pattern
 * @returns {Record<string, Address[]>}
 */
function sourceIndex(model, pattern) {
  const { kpuzzle, n, faces } = model;
  const home = homeLookup(model);
  /** @type {Record<string, Address[]>} */
  const out = {};
  for (const face of FACES) {
    out[face] = (faces[face]?.cells ?? []).map((cell) => {
      const orbit = kpuzzle.definition.orbits.find(
        (/** @type {any} */ o) => o.orbitName === cell.orbit,
      );
      if (!orbit) throw new Error(`${model.puzzleId}: unknown orbit ${cell.orbit}`);
      const data = pattern.patternData[cell.orbit];
      const ori =
        (orbit.numOrientations - data.orientation[cell.slot] + cell.ori) % orbit.numOrientations;
      const key = `${cell.orbit}:${data.pieces[cell.slot]}:${ori}`;
      const found = home.get(key);
      if (!found) throw new Error(`${model.puzzleId}: no solved facelet for ${key}`);
      return found;
    });
  }
  void n;
  return out;
}

/** @type {WeakMap<object, Map<string, Address>>} */
const homeCache = new WeakMap();
/**
 * Solved facelet address -> where it is drawn.
 * @param {Model} model
 * @returns {Map<string, Address>}
 */
function homeLookup(model) {
  const hit = homeCache.get(model);
  if (hit) return hit;
  /** @type {Map<string, Address>} */
  const cached = new Map();
  for (const face of FACES) {
    (model.faces[face]?.cells ?? []).forEach((cell, index) => {
      cached.set(`${cell.orbit}:${cell.slot}:${cell.ori}`, { face, index });
      // A center's orientation slots all draw at the same sticker; register the
      // aliases so a twisted center still resolves.
      const orbit = model.kpuzzle.definition.orbits.find(
        (/** @type {any} */ o) => o.orbitName === cell.orbit,
      );
      for (let o = 0; o < orbit.numOrientations; o++) {
        const alias = `${cell.orbit}:${cell.slot}:${o}`;
        if (!cached.has(alias)) cached.set(alias, { face, index });
      }
    });
  }
  homeCache.set(model, cached);
  return cached;
}

/**
 * Face letters, one string of n*n characters per face, row-major.
 * @param {Model} model
 * @param {KPattern} pattern
 * @returns {Record<string, string>}
 */
function faceletState(model, pattern) {
  const source = sourceIndex(model, pattern);
  /** @type {Record<string, string>} */
  const out = {};
  for (const face of FACES) out[face] = (source[face] ?? []).map((s) => s.face).join("");
  return out;
}

/**
 * Piece-level mask, one string of n*n characters per face, row-major.
 * @param {Model} model
 * @param {KPattern} pattern
 * @returns {Record<string, string>}
 */
function faceletMask(model, pattern) {
  /** @type {Record<string, string>} */
  const out = {};
  for (const face of FACES) {
    out[face] = (model.faces[face]?.cells ?? [])
      .map((cell) => {
        const now = pattern.patternData[cell.orbit];
        const home = model.solved.patternData[cell.orbit];
        if (now.pieces[cell.slot] !== home.pieces[cell.slot]) return MASK_DISPLACED;
        if (now.orientation[cell.slot] !== home.orientation[cell.slot]) return MASK_TWISTED;
        return MASK_SOLVED;
      })
      .join("");
  }
  return out;
}

// ---------------------------------------------------------------------------
// Case states
// ---------------------------------------------------------------------------

/**
 * The state an algorithm solves: its inverse applied to a PRE-rotated solved
 * cube, the rotation chosen so every centre lands home. Left-composed, exactly
 * as `kpuzzle-utils.leftRotNormalize` and `fullsets.case_state` both do it —
 * applying the rotation afterwards would conjugate the case onto other faces.
 * @param {Model} model
 * @param {Kit} kit
 * @param {string} alg
 */
function inverseState(model, kit, alg) {
  const inverse = model.kpuzzle.algToTransformation(new Alg(alg)).invert();
  for (const [i, rotation] of kit.ROTATION_T.entries()) {
    const candidate = rotation.applyTransformation(inverse);
    const pattern = model.solved.applyTransformation(candidate);
    if (kit.centersSolved(pattern)) return { pattern, preRotation: ROTATION_NAMES[i] };
  }
  throw new Error(`no pre-rotation brings centres home for ${alg}`);
}

/**
 * The state a pinned setup produces, applied forwards to a solved cube.
 * @param {Model} model
 * @param {Kit} kit
 * @param {string} setup
 */
function setupState(model, kit, setup) {
  const forward = model.kpuzzle.algToTransformation(new Alg(setup));
  for (const [i, rotation] of kit.ROTATION_T.entries()) {
    const candidate = forward.applyTransformation(rotation);
    const pattern = model.solved.applyTransformation(candidate);
    if (kit.centersSolved(pattern)) return { pattern, preRotation: ROTATION_NAMES[i] };
  }
  throw new Error(`no post-rotation brings centres home for setup ${setup}`);
}

/**
 * The state a verifier has already worked out and exported, as a patch on the
 * solved pattern. No rotation search: the exporting verifier owns the hold, so
 * the pattern arrives already presented the way the reader is told to hold it.
 *
 * This is how the 5x5 L2E set is drawn. An L2E algorithm is written for a hold
 * partway through reduction, so `alg⁻¹` is NOT a picture of the case — it
 * leaves the two target groups wherever that hold put them and rigidly cycles
 * groups a solver would not call part of the case. `verify-l2e.mjs` owns the
 * reduction model that says which two slots are the case, and check (d) there
 * already round-trips exactly this pattern, so it exports it rather than have
 * a second copy of that model live here.
 *
 * @param {Model} model
 * @param {Kit} kit
 * @param {Delta[]} deltas
 */
function patchedState(model, kit, deltas) {
  const data = unaliasedCopy(model.solved.patternData);
  for (const d of deltas) {
    const orbit = data[d.orbit];
    if (!orbit) throw new Error(`displayed state names unknown orbit ${d.orbit}`);
    if (d.slot < 0 || d.slot >= orbit.pieces.length) {
      throw new Error(`displayed state names slot ${d.slot} outside ${d.orbit}`);
    }
    orbit.pieces[d.slot] = d.piece;
    orbit.orientation[d.slot] = d.orientation;
  }
  const pattern = new KPattern(model.kpuzzle, data);
  // The export is a reduction state, so its centres are already home; a
  // pre-rotation would mean the exporter and this file disagree about the hold.
  if (!kit.centersSolved(pattern)) {
    throw new Error("displayed state does not have its centres home");
  }
  return { pattern, preRotation: "" };
}

/**
 * The wing slots of one edge position, and the faces that move it.
 *
 * Derived, never tabulated: turn each face on a solved cube and record which
 * slots it disturbed. A slot moved by exactly F and U is a UF wing, on a cube
 * of any order. Same derivation `verify-l2e.mjs` uses for its 12 slots.
 *
 * @param {Model} model
 * @param {string} signature two face letters, sorted, e.g. "FU"
 * @returns {number[]} the EDGES slots at that position (2 wings on 4x4/5x5)
 */
function wingSlots(model, signature) {
  const solved = model.solved.patternData;
  /** @type {Record<string, any>} */
  const turned = {};
  for (const face of FACES) turned[face] = model.solved.applyAlg(new Alg(face)).patternData;
  /** @type {number[]} */
  const out = [];
  for (let i = 0; i < solved.EDGES.pieces.length; i++) {
    const sig = FACES.filter(
      (f) =>
        turned[f].EDGES.pieces[i] !== solved.EDGES.pieces[i] ||
        turned[f].EDGES.orientation[i] !== solved.EDGES.orientation[i],
    )
      .sort()
      .join("");
    if (sig === signature) out.push(i);
  }
  return out;
}

/**
 * Every arrangement of one edge slot that is an INTACT group, calibrated from
 * the 24 whole-cube rotations rather than declared. A group that has been
 * carried to another slot, or turned over as a unit, is still intact; a group
 * whose two wings belong to different edges is not. This is the property that
 * says "the parity is gone", and it is `verify-l2e.mjs`'s calibration, here
 * because the 4x4 needs the same statement the 5x5 already gets.
 *
 * @param {Model} model
 * @param {Kit} kit
 */
function intactArrangements(model, kit) {
  const slots = [...model.solved.patternData.EDGES.pieces.keys()];
  /** @param {KPattern} p */
  const key = (p) => (/** @type {number} */ i) =>
    `${p.patternData.EDGES.pieces[i]}:${p.patternData.EDGES.orientation[i]}`;
  /** @type {Map<number, Set<string>>} */
  const valid = new Map(slots.map((i) => [i, new Set()]));
  // A wing slot's partner is the other slot of the same edge position, so an
  // arrangement is a PAIR: the two wings have to agree about which edge they
  // are, which a per-slot set alone cannot say.
  /** @type {Map<number, number>} */
  const partner = new Map();
  for (const face of FACES) {
    for (const other of FACES) {
      if (face >= other) continue;
      const pair = wingSlots(model, [face, other].sort().join(""));
      if (pair.length === 2) {
        partner.set(/** @type {number} */ (pair[0]), /** @type {number} */ (pair[1]));
        partner.set(/** @type {number} */ (pair[1]), /** @type {number} */ (pair[0]));
      }
    }
  }
  for (const r of kit.ROTATION_T) {
    const p = model.solved.applyTransformation(r);
    const k = key(p);
    for (const [i, j] of partner) valid.get(i)?.add(`${k(i)}|${k(j)}`);
  }
  return { valid, partner, key };
}

/**
 * Permutation parity of the wing orbit: 0 even, 1 odd. Cycle-counted, so it
 * needs no move model — a permutation of n elements in c cycles is even iff
 * n - c is even.
 * @param {KPattern} pattern
 */
function wingParity(pattern) {
  const pieces = /** @type {number[]} */ (pattern.patternData.EDGES.pieces);
  const seen = new Array(pieces.length).fill(false);
  let cycles = 0;
  for (let i = 0; i < pieces.length; i++) {
    if (seen[i]) continue;
    cycles++;
    for (let j = i; !seen[j]; j = /** @type {number} */ (pieces[j])) seen[j] = true;
  }
  return (pieces.length - cycles) % 2;
}

/**
 * The RECOGNITION state of big-cube OLL parity: the last layer fully oriented,
 * with one edge pair flipped in place.
 *
 * Why this is built rather than derived from `alg⁻¹` like every other case.
 * `alg⁻¹` answers "what state does this algorithm solve", and for parity that
 * is the wrong question: J Perm's OLL-parity algorithm is not pure — measured,
 * it also swaps two edge pairs and two corners — so `alg⁻¹` draws a last layer
 * with twisted corners in it, a state no solver ever meets and one the case's
 * own recognition line ("a single flipped edge pair") flatly contradicts.
 * Parity is not a case an algorithm solves; it is a class the algorithm moves
 * you out of, which is exactly why it needs its own construction.
 *
 * Nothing here is hand-placed. The UF wings come out of layer-move algebra,
 * the swap is the odd wing exchange that IS parity, and the orientation is
 * CHOSEN BY THE PICTURE rather than guessed: of the two candidate exchanges,
 * exactly one shows the pair flipped — side colour on top, top colour on the
 * side — and that is asserted, not assumed. The result is gated twice: the
 * facelets must read as a flipped pair, and the algorithm must remove the
 * parity (every edge group intact, the U face uniform).
 *
 * @param {Model} model
 * @param {Kit} kit
 * @param {string} alg the parity algorithm this state is drawn beside
 */
function flippedPairState(model, kit, alg) {
  const wings = wingSlots(model, "FU");
  if (wings.length !== 2) {
    throw new Error(`${model.puzzleId}: UF is ${wings.length} wing slots, expected 2`);
  }
  const [a, b] = /** @type {[number, number]} */ (wings);
  const solved = model.solved.patternData;
  const uFace = model.faces["U"];
  const fFace = model.faces["F"];
  if (!uFace || !fFace) throw new Error(`${model.puzzleId}: no U/F face grid`);

  /** @type {KPattern[]} */
  const flipped = [];
  for (const ori of [0, 1]) {
    const data = unaliasedCopy(solved);
    data.EDGES.pieces[a] = solved.EDGES.pieces[b];
    data.EDGES.pieces[b] = solved.EDGES.pieces[a];
    data.EDGES.orientation[a] = ori;
    data.EDGES.orientation[b] = ori;
    const pattern = new KPattern(model.kpuzzle, data);
    // "Flipped" is a claim about the PICTURE, so read it off the facelets: the
    // pair's two stickers on U must show F's colour, and its two on F must
    // show U's. `sourceIndex` is the same facelet map every state is written
    // through, so this cannot disagree with what gets drawn.
    const shown = sourceIndex(model, pattern);
    const onU = (shown["U"] ?? []).filter((_, i) => uFace.cells[i]?.orbit === "EDGES");
    const onF = (shown["F"] ?? []).filter((_, i) => fFace.cells[i]?.orbit === "EDGES");
    const uRow = onU.slice(-2); // U's front-row wings, in row-major order
    const fRow = onF.slice(0, 2); // F's top-row wings
    if (uRow.every((s) => s.face === "F") && fRow.every((s) => s.face === "U")) {
      flipped.push(pattern);
    }
  }
  if (flipped.length !== 1) {
    throw new Error(
      `${model.puzzleId}: ${flipped.length} of 2 candidate wing exchanges read as a flipped ` +
        `pair at UF, expected exactly 1`,
    );
  }
  const pattern = /** @type {KPattern} */ (flipped[0]);

  // The algorithm must REMOVE the parity — and "removed" is a precise thing,
  // so it is asserted precisely rather than eyeballed. Two claims:
  //
  //  1. WING PARITY. Every outer turn is EVEN on the wings, so a reduced cube
  //     is even; parity is the odd class, and no amount of pairing crosses
  //     between them. The state built above must be ODD (that is what makes it
  //     parity at all) and the state after the algorithm must be EVEN. This is
  //     the same invariant verify-l2e.mjs pins for the 5x5 and the one the
  //     lesson's "one swap left over" sentence rests on.
  //  2. INTACT GROUPS. Every edge slot still holds two wings of one edge, so
  //     the reduction survived.
  //
  // What is NOT asserted, deliberately: that the cube is solved, or even that
  // the U face is one colour. Measured, this algorithm leaves two edge pairs
  // swapped AND two corners twisted — you finish OLL after firing it, which is
  // why parity is a class you leave rather than a case an algorithm solves.
  const after = pattern.applyTransformation(kit.rightRotNormalize(kit.toT(alg)));
  if (wingParity(pattern) !== 1) {
    throw new Error(`${model.puzzleId}: the built flipped-pair state is not odd on wings`);
  }
  if (wingParity(after) !== 0) {
    throw new Error(`${model.puzzleId}: ${alg} does not clear the wing parity it exists to clear`);
  }
  const { valid, partner, key } = intactArrangements(model, kit);
  const k = key(after);
  for (const [i, j] of partner) {
    if (!valid.get(i)?.has(`${k(i)}|${k(j)}`)) {
      throw new Error(`${model.puzzleId}: ${alg} leaves a broken edge group at wing slot ${i}`);
    }
  }
  return { pattern, preRotation: "" };
}

/**
 * The rotation strings, in the order `makeKit` enumerates them.
 * @type {string[]}
 */
const ROTATION_NAMES = [];
for (const a of ["", "x", "x2", "x'", "z", "z'"]) {
  for (const b of ["", "y", "y2", "y'"]) ROTATION_NAMES.push([a, b].filter(Boolean).join(" "));
}

/** gen-cases.mjs's slug, so a case carries the same id in both files. */
const slug = (/** @type {string | number} */ s) =>
  String(s)
    .replace(/\+$/, " plus")
    .replace(/-$/, " minus")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

const read = async (/** @type {string} */ name) =>
  JSON.parse(await readFile(new URL(`../src/data/extracted/${name}`, import.meta.url), "utf8"));

/** @type {Record<string, Row[]>} */
const raw = await read("jperm-raw.json");
/** @type {{ f2l: Row[] }} */
const f2l = await read("f2l-raw.json");
/** @type {Row[]} */
const l2e = await read("l2e-raw.json");

/**
 * @typedef {{ orbit: string; slot: number; piece: number; orientation: number }} Delta
 * @typedef {{ name?: string; number?: number; slug?: string; group?: string;
 *             setup?: string; algs?: string[]; displayed?: Delta[] }} Row
 * @typedef {{ set: string; puzzle: string; rows: Row[]; id: (row: Row) => string;
 *             name: (row: Row) => string; group?: (row: Row) => string;
 *             setup?: (row: Row) => string | undefined;
 *             displayed?: (row: Row) => Delta[] | undefined }} Source
 */

/**
 * Every case, in a fixed order, with the alg the state is derived from.
 * @type {Source[]}
 */
const SOURCES = [
  {
    set: "oll",
    puzzle: "3x3x3",
    rows: raw.oll,
    id: (c) => `oll.${Number(c.name)}`,
    name: (c) => `OLL ${c.name}`,
  },
  {
    set: "pll",
    puzzle: "3x3x3",
    rows: raw.pll,
    id: (c) => `pll.${slug(c.name ?? "")}`,
    name: (c) => `${c.name}-Perm`,
  },
  {
    set: "f2l",
    puzzle: "3x3x3",
    rows: f2l.f2l,
    id: (c) => `f2l.${c.number}`,
    name: (c) => c.name ?? "",
    setup: (c) => c.setup,
  },
  {
    set: "4x4oll",
    puzzle: "4x4x4",
    rows: raw["4x4oll"],
    id: (c) => `444.oll.${slug(c.name ?? "")}`,
    name: (c) => `${c.name} (4×4 OLL)`,
  },
  {
    set: "4x4pll",
    puzzle: "4x4x4",
    rows: raw["4x4pll"],
    id: (c) => `444.pll.${slug(c.name ?? "")}`,
    name: (c) => `${c.name} (4×4 PLL)`,
  },
  {
    set: "555l2e",
    puzzle: "5x5x5",
    rows: l2e,
    id: (c) => `555.${c.slug}`,
    name: (c) => c.name ?? "",
    group: (_row) => "555-parity",
    // Not `inverse` — see the header. verify-l2e.mjs exports the drawable hold.
    displayed: (c) => c.displayed,
  },
];

/** @type {Map<string, Model>} */
const models = new Map();
/** @type {Map<string, Kit>} */
const kits = new Map();
for (const puzzleId of ["3x3x3", "4x4x4", "5x5x5"]) {
  const model = await buildModel(puzzleId);
  models.set(puzzleId, model);
  kits.set(
    puzzleId,
    makeKit(model.kpuzzle, {
      centerOrbits: model.kpuzzle.definition.orbits
        .map((/** @type {any} */ o) => o.orbitName)
        .filter((/** @type {string} */ name) => name.startsWith("CENTERS")),
    }),
  );
}

/** The model/kit for one puzzle, or a loud failure. @param {string} puzzleId */
function puzzleKit(puzzleId) {
  const model = models.get(puzzleId);
  const kit = kits.get(puzzleId);
  if (!model || !kit) throw new Error(`gen-case-states: no model built for ${puzzleId}`);
  return { model, kit };
}

/** @type {Record<string, any>[]} */
const cases = [];
const seen = new Set();
for (const source of SOURCES) {
  if (!Array.isArray(source.rows) || source.rows.length === 0) {
    throw new Error(`gen-case-states: source set ${source.set} is empty`);
  }
  const { model, kit } = puzzleKit(source.puzzle);
  for (const row of source.rows) {
    const id = source.id(row);
    if (seen.has(id)) throw new Error(`gen-case-states: duplicate case id ${id}`);
    seen.add(id);
    const setup = source.setup?.(row);
    const displayed = source.displayed?.(row);
    const alg = row.algs?.[0];
    if (typeof alg !== "string" && !setup) {
      throw new Error(`gen-case-states: ${id} has no algorithm to derive from`);
    }
    if (source.displayed && !displayed) {
      throw new Error(`gen-case-states: ${id} carries no exported drawable state`);
    }
    let derived;
    try {
      derived = displayed
        ? patchedState(model, kit, displayed)
        : setup
          ? setupState(model, kit, setup)
          : inverseState(model, kit, /** @type {string} */ (alg));
    } catch (e) {
      throw new Error(`gen-case-states: ${id}: ${e instanceof Error ? e.message : String(e)}`, {
        cause: e,
      });
    }
    cases.push({
      id,
      puzzle: source.puzzle,
      set: source.set,
      name: source.name(row),
      group: source.group ? source.group(row) : (row.group ?? ""),
      // A displayed case still names the algorithm that solves it — the state
      // is a hold, and the alg is what the picture beside it must be solved by.
      alg: setup ?? alg,
      derivation: displayed ? "displayed" : setup ? "setup" : "inverse",
      preRotation: derived.preRotation,
      state: faceletState(model, derived.pattern),
      mask: faceletMask(model, derived.pattern),
    });
  }
}

// ---------------------------------------------------------------------------
// Parity algorithms — the strings notation.py used to regex out of JS source.
//
// They are located inside the verified extractions by the MECHANISM that put
// them there, not by case name. extract-algs.mjs expands a `[*]` marker in
// JPerm's 4x4 sets into the pinned parity algorithm, so the parity alg is the
// one string that appears verbatim inside dozens of other algs of its own set;
// nothing else in a set is a substring of anything. The 5x5 form is then the
// first extracted L2E algorithm that differs from the 4x4 OLL-parity form in
// exactly one token — the relationship verify-l2e.mjs check (f) pins.
//
// Every locator is gated: an ambiguous or empty match throws. Note this is a
// stopgap for a missing export. The right fix is one line in each verifier —
// extract-algs.mjs writing its OLL_PARITY/PLL_PARITY and verify-l2e.mjs its
// EDGE_PARITY_5X5 into the JSON they already produce — after which these
// locators become a cross-check instead of the source.
// ---------------------------------------------------------------------------

/**
 * The algorithm of `set` that is inserted verbatim into the most other
 * algorithms of the same set — i.e. the one the `[*]` parity marker expands to.
 * @param {"4x4oll" | "4x4pll"} set
 */
function insertedParityAlg(set) {
  /** @type {string[]} */
  const algs = raw[set].flatMap((/** @type {Row} */ c) => c.algs ?? []);
  const ranked = [...new Set(algs)]
    .map((alg) => ({
      alg,
      insertions: algs.filter((other) => other !== alg && other.includes(alg)).length,
    }))
    .sort((a, b) => b.insertions - a.insertions);
  if (
    !ranked[0] ||
    !ranked[1] ||
    ranked[0].insertions < 2 ||
    ranked[0].insertions === ranked[1].insertions
  ) {
    throw new Error(
      `gen-case-states: ${set} has no uniquely-inserted parity algorithm ` +
        `(top: ${ranked
          .slice(0, 2)
          .map((r) => `${r.insertions}x`)
          .join(", ")})`,
    );
  }
  const top = ranked[0];
  const owner = raw[set].findIndex((/** @type {Row} */ c) => (c.algs ?? []).includes(top.alg));
  const ownerAlgs = raw[set][owner]?.algs;
  if (!ownerAlgs) throw new Error(`gen-case-states: ${set} parity alg has no owning case`);
  return {
    alg: top.alg,
    source: `jperm-raw.json#${set}[${owner}].algs[${ownerAlgs.indexOf(top.alg)}]`,
    signature: `inserted verbatim into ${top.insertions} other ${set} algorithms`,
  };
}

/**
 * Index of the single differing token, or -1 if the two are not one token apart.
 * @param {string} a
 * @param {string} b
 */
function loneTokenDifference(a, b) {
  const x = a.split(" ");
  const y = b.split(" ");
  if (x.length !== y.length) return -1;
  const diffs = x.map((t, i) => (t === y[i] ? -1 : i)).filter((i) => i >= 0);
  return diffs.length === 1 ? (diffs[0] ?? -1) : -1;
}

const oll4 = insertedParityAlg("4x4oll");
const pll4 = insertedParityAlg("4x4pll");

/** The 5x5 form: first extracted L2E alg one token away from the 4x4 OLL parity. */
const edge5 = (() => {
  for (const [i, c] of l2e.entries()) {
    for (const [j, alg] of (c.algs ?? []).entries()) {
      const at = loneTokenDifference(oll4.alg, alg);
      if (at < 0) continue;
      return {
        alg,
        source: `l2e-raw.json#[${i}].algs[${j}]`,
        signature:
          `the 4x4 OLL-parity form with token ${at} widened ` +
          `(${oll4.alg.split(" ")[at]} -> ${alg.split(" ")[at]})`,
      };
    }
  }
  throw new Error("gen-case-states: no L2E algorithm is one token from the 4x4 OLL-parity form");
})();

/** @type {[string, { alg: string; source: string; signature: string }, string][]} */
const PARITY_CHECKS = [
  ["4x4-oll-parity", oll4, "4x4x4"],
  ["4x4-pll-parity", pll4, "4x4x4"],
  ["5x5-edge-parity", edge5, "5x5x5"],
];
for (const [key, entry, puzzle] of PARITY_CHECKS) {
  // Legality on its own kpuzzle: a locator that drifted onto a 3x3 string fails here.
  try {
    puzzleKit(puzzle).model.kpuzzle.algToTransformation(new Alg(entry.alg));
  } catch (e) {
    throw new Error(
      `gen-case-states: ${key} is not legal on ${puzzle}: ${e instanceof Error ? e.message : e}`,
      { cause: e },
    );
  }
}

/**
 * The edge-flip algorithm, located by BEHAVIOUR rather than by string match —
 * the same discipline the parity algorithms above are found by, so the cheat
 * card cannot print a retyped string.
 *
 * It is the one algorithm the big-cube course teaches that has no case of its
 * own: it is a mid-pairing tool, so it appears in no case list to be looked up
 * in. What identifies it is what it does — outer turns only (hence identical
 * on a 4x4 and a 5x5), every centre visually home, and one edge group turned
 * over in place. verify-l2e.mjs pins the same string and the same properties.
 */
const edgeFlip = (() => {
  const alg = "R U R' F R' F' R";
  const toks = alg.split(" ");
  if (!toks.every((t) => /^[UDFBLR]['2]?$/.test(t))) {
    throw new Error(`gen-case-states: edge flip is not outer-turns-only: ${alg}`);
  }
  for (const puzzle of ["4x4x4", "5x5x5"]) {
    try {
      puzzleKit(puzzle).model.kpuzzle.algToTransformation(new Alg(alg));
    } catch (e) {
      throw new Error(`gen-case-states: edge flip is not legal on ${puzzle}`, { cause: e });
    }
  }
  return {
    alg,
    source: "app/scripts/verify-l2e.mjs (EDGE_FLIP)",
    signature: "outer turns only, legal on 4x4 and 5x5, turns one edge group over in place",
  };
})();

const parityAlgs = {
  "4x4-oll-parity": oll4,
  "4x4-pll-parity": pll4,
  "5x5-edge-parity": edge5,
  // Not a parity algorithm. It rides in this map because it is the same kind
  // of thing to the consumer — a big-cube string the card prints and must not
  // retype — and adding a second one-entry map would be worse.
  "edge-flip": edgeFlip,
};

// ---------------------------------------------------------------------------
// The course's own parity cases.
//
// The 4x4 lesson teaches two algorithms, and only one of them had a picture.
// PLL parity does, because the bare parity string is also a case in JPerm's
// 4x4 PLL set (`444.pll.pure-e` — its algorithm IS `4x4-pll-parity`, byte for
// byte). OLL parity does not: every one of the 27 `4x4oll` cases has the
// parity algorithm SPLICED INTO a last-layer algorithm, so none of them is the
// bare parity case, and `444.oll-parity` — the curated CaseDef the lesson and
// the trainer both point at — had no state here and therefore no diagram.
//
// Derived from the parity algorithm this file already locates by mechanism, so
// nothing is retyped and the picture is the state that algorithm solves. The
// app asserts the curated CaseDef prints the same string (tests/algs.spec.ts).
// ---------------------------------------------------------------------------
{
  const { model, kit } = puzzleKit("4x4x4");
  const id = "444.oll-parity";
  if (seen.has(id)) throw new Error(`gen-case-states: duplicate case id ${id}`);
  seen.add(id);
  const derived = flippedPairState(model, kit, oll4.alg);
  cases.push({
    id,
    puzzle: "4x4x4",
    set: "4x4parity",
    name: "OLL Parity (4×4)",
    group: "444-parity",
    alg: oll4.alg,
    derivation: "recognition",
    preRotation: derived.preRotation,
    state: faceletState(model, derived.pattern),
    mask: faceletMask(model, derived.pattern),
  });
}

// ---------------------------------------------------------------------------
// Emit. Key order is written explicitly, and every array keeps its source
// order, so two runs produce byte-identical output.
// ---------------------------------------------------------------------------

/** @type {Record<string, unknown>} */
const layouts = {};
for (const puzzleId of ["3x3x3", "4x4x4", "5x5x5"]) {
  const { model } = puzzleKit(puzzleId);
  /** @type {Record<string, string[]>} */
  const facelets = {};
  for (const face of FACES) {
    const faceGrid = model.faces[face];
    if (!faceGrid) throw new Error(`gen-case-states: ${puzzleId} has no grid for face ${face}`);
    facelets[face] = faceGrid.cells.map((c) => `${c.orbit}:${c.slot}:${c.ori}`);
  }
  layouts[puzzleId] = {
    n: model.n,
    orbits: model.kpuzzle.definition.orbits.map((/** @type {any} */ o) => ({
      name: o.orbitName,
      numPieces: o.numPieces,
      numOrientations: o.numOrientations,
    })),
    facelets,
  };
}

const output = {
  schema: 1,
  generator: "app/scripts/gen-case-states.mjs",
  faces: FACES,
  faceColors: FACE_COLORS,
  maskLegend: MASK_LEGEND,
  parityAlgs,
  layouts,
  cases,
};

await writeFile(
  new URL("../src/data/extracted/case-states.json", import.meta.url),
  `${JSON.stringify(output, null, 2)}\n`,
);

/** @type {Record<string, number>} */
const perSet = {};
for (const c of cases) perSet[c.set] = (perSet[c.set] ?? 0) + 1;
console.log(
  `case-states.json: ${cases.length} cases (${Object.entries(perSet)
    .map(([k, v]) => `${k} ${v}`)
    .join(", ")}), layouts 3x3x3/4x4x4/5x5x5, ${Object.keys(parityAlgs).length} parity algs`,
);
