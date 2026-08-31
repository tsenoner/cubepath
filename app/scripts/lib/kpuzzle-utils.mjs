/**
 * Shared kpuzzle verification kit for the extraction/verification scripts
 * (extract-algs.mjs, verify-f2l.mjs, verify-l2e.mjs, gen-case-states.mjs):
 * rotation enumeration, transformation helpers, rotation-normalization, and
 * the aliasing-safe pattern copy every exporter needs.
 */
import { Alg } from "cubing/alg";

/** All 24 whole-cube orientations as rotation strings ("" = identity). */
export const ROTATIONS = [];
for (const a of ["", "x", "x2", "x'", "z", "z'"]) {
  for (const b of ["", "y", "y2", "y'"]) ROTATIONS.push([a, b].filter(Boolean).join(" "));
}

/**
 * Build the per-puzzle kit. `centerOrbits` lists the orbit names whose pieces
 * must match solved for "centers visually home" (3x3: ["CENTERS"]; the 5x5
 * adds CENTERS2/CENTERS3).
 */
export function makeKit(kpuzzle, { centerOrbits = ["CENTERS"] } = {}) {
  const solved = kpuzzle.defaultPattern();
  const ID = kpuzzle.identityTransformation();
  const toT = (s) => (s ? kpuzzle.algToTransformation(new Alg(s)) : ID);
  const ROTATION_ALGS = ROTATIONS.map((r) => (r ? new Alg(r) : null));
  const ROTATION_T = ROTATIONS.map(toT);
  const AUF_T = ["", "U", "U2", "U'"].map(toT);

  const centersSolved = (pattern) =>
    centerOrbits.every((o) =>
      pattern.patternData[o].pieces.every((v, i) => v === solved.patternData[o].pieces[i]),
    );

  /** Rotate a PATTERN so its centers are home; throws if impossible. */
  const normalizePattern = (pattern) => {
    for (const r of ROTATION_ALGS) {
      const p = r ? pattern.applyAlg(r) : pattern;
      if (centersSolved(p)) return p;
    }
    throw new Error("normalizePattern: no rotation brings centers home");
  };

  /**
   * Cancel a transformation's net whole-cube rotation. Forward states are a
   * physically rotated cube — rotate back AFTER, i.e. right-compose. Inverted
   * transformations (pre-states, alg⁻¹) carry any net rotation on the LEFT —
   * left-compose. Using the wrong side conjugates the state onto the wrong
   * faces. Both throw when no rotation brings centers home.
   */
  const rightRotNormalize = (t) => {
    for (const r of ROTATION_T) {
      const cand = t.applyTransformation(r);
      if (centersSolved(solved.applyTransformation(cand))) return cand;
    }
    throw new Error("rightRotNormalize: no rotation brings centers home");
  };
  const leftRotNormalize = (t) => {
    for (const r of ROTATION_T) {
      const cand = r.applyTransformation(t);
      if (centersSolved(solved.applyTransformation(cand))) return cand;
    }
    throw new Error("leftRotNormalize: no rotation brings centers home");
  };

  return {
    solved,
    ID,
    toT,
    ROTATION_ALGS,
    ROTATION_T,
    AUF_T,
    centersSolved,
    normalizePattern,
    rightRotNormalize,
    leftRotNormalize,
  };
}

/**
 * Slot kit: the base kit plus U-layer / FR-slot piece-slot maps and the
 * layer-local invariant predicates shared by verify-f2l.mjs and
 * tests/algs.spec.ts. Slots are detected mechanically, never hardcoded:
 * the U layer is whatever moves under U; the FR slot is whatever moves
 * under R and F but not U (3x3: the DFR corner + FR edge).
 */
export function makeSlotKit(kpuzzle, kit = makeKit(kpuzzle)) {
  const { solved } = kit;
  const uTurn = solved.applyAlg(new Alg("U")).patternData;
  const rTurn = solved.applyAlg(new Alg("R")).patternData;
  const fTurn = solved.applyAlg(new Alg("F")).patternData;
  const movedBy = (turn, orbit, i) => {
    const s = solved.patternData[orbit];
    return turn[orbit].pieces[i] !== s.pieces[i] || turn[orbit].orientation[i] !== s.orientation[i];
  };
  const U_SLOTS = {};
  const FR_SLOTS = {};
  const FR_PIECE = {}; // orbit -> piece id of the FR-pair piece
  for (const orbit of Object.keys(solved.patternData)) {
    const n = solved.patternData[orbit].pieces.length;
    U_SLOTS[orbit] = Array.from({ length: n }, (_, i) => movedBy(uTurn, orbit, i));
    FR_SLOTS[orbit] = Array.from(
      { length: n },
      (_, i) => movedBy(rTurn, orbit, i) && !movedBy(uTurn, orbit, i) && movedBy(fTurn, orbit, i),
    );
    const idxs = FR_SLOTS[orbit].flatMap((v, i) => (v ? [i] : []));
    if (idxs.length > 1) {
      throw new Error(`FR-slot detection: ${orbit} matched ${idxs.length} slots`);
    }
    if (idxs.length === 1) FR_PIECE[orbit] = solved.patternData[orbit].pieces[idxs[0]];
  }

  /** Every piece outside the U layer solved? (allowFRSlot also exempts the FR slot.) */
  const outsideSolved = (pattern, { allowFRSlot }) => {
    const d = pattern.patternData;
    for (const orbit of Object.keys(d)) {
      const s = solved.patternData[orbit];
      for (let i = 0; i < s.pieces.length; i++) {
        if (U_SLOTS[orbit][i] || (allowFRSlot && FR_SLOTS[orbit][i])) continue;
        if (d[orbit].pieces[i] !== s.pieces[i] || d[orbit].orientation[i] !== s.orientation[i]) {
          return false;
        }
      }
    }
    return true;
  };

  /**
   * Every U-layer edge and corner in solved orientation? (The pure-permutation
   * half of the PLL invariant. CENTERS orbits are skipped — center twist is
   * invisible on a standard cube.)
   */
  const uLayerOriented = (pattern) => {
    for (const orbit of Object.keys(solved.patternData)) {
      if (orbit.startsWith("CENTERS")) continue;
      const d = pattern.patternData[orbit];
      const s = solved.patternData[orbit];
      for (let i = 0; i < s.pieces.length; i++) {
        if (U_SLOTS[orbit][i] && d.orientation[i] !== s.orientation[i]) return false;
      }
    }
    return true;
  };

  return { ...kit, U_SLOTS, FR_SLOTS, FR_PIECE, outsideSolved, uLayerOriented };
}

/**
 * A copy of a pattern's data whose orbits share no arrays.
 *
 * `structuredClone` is NOT safe here and this is not a style preference.
 * cubing.js's `defaultPattern()` hands every orbit of the same length the SAME
 * zero-filled orientation array — on the 5x5, EDGES, CENTERS and CENTERS2 are
 * all 24 slots and all three are literally one array — and `structuredClone`
 * faithfully preserves that aliasing. So `synth.EDGES.orientation[i] = 1` also
 * wrote CENTERS.orientation[i] and CENTERS2.orientation[i].
 *
 * It was invisible: `centersSolved` compares pieces only, and CENTERS has
 * numOrientations 1, so a bogus centre orientation changes no check and no
 * picture. It stops being invisible the moment the pattern is EXPORTED —
 * a delta reads orientation, and every case came out claiming centre twists it
 * does not have. verify-l2e.mjs asserts the aliasing is still there rather
 * than trusting this comment.
 *
 * Lives here because every writer of an exported pattern needs it:
 * verify-l2e.mjs builds its synthetic holds, gen-case-states.mjs patches the
 * displayed state and builds the 4x4 flipped pair.
 *
 * @param {Record<string, { pieces: number[]; orientation: number[] }>} data
 * @returns {Record<string, { pieces: number[]; orientation: number[] }>}
 */
export function unaliasedCopy(data) {
  /** @type {Record<string, { pieces: number[]; orientation: number[] }>} */
  const out = {};
  for (const orbit of Object.keys(data)) {
    out[orbit] = {
      pieces: [...data[orbit].pieces],
      orientation: [...data[orbit].orientation],
    };
  }
  return out;
}

// ── The big-cube reduction model ────────────────────────────────────────────
// verify-l2e.mjs (5x5) and gen-case-states.mjs (4x4) both need to say the same
// three things about a reduced cube: where the edge positions are, whether a
// position still holds one whole edge, and whether the wing permutation is odd.
// They said them twice, in two styles, and the 4x4 copy gates a SHIPPED diagram
// while the 5x5 copy gates the exported case data — so a correction to either
// convention silently left the other on the old one. One statement now, with
// the order and the orbit names as parameters.

/** The six face turns, as move strings. */
const EDGE_FACES = ["U", "D", "L", "R", "F", "B"];

/**
 * Every edge POSITION of a cube, keyed by the two faces that move it.
 *
 * Derived, never tabulated: turn each face on a solved cube and note which
 * slots it disturbed, so a slot moved by exactly F and U is a UF slot at ANY
 * order. A 4x4/5x5 position holds two wings; a 5x5 also has a midge (`EDGES2`),
 * and `midgeOrbit: null` is how a 4x4 says it has none.
 *
 * @param {any} solved the puzzle's default pattern
 * @param {(s: string) => any} toT
 * @param {{ wingOrbit?: string; midgeOrbit?: string | null }} [opts]
 * @returns {Record<string, { wings: number[]; midge: number }>} signature -> slots
 */
export function edgeSlots(solved, toT, { wingOrbit = "EDGES", midgeOrbit = null } = {}) {
  const turned = Object.fromEntries(
    EDGE_FACES.map((f) => [f, solved.applyTransformation(toT(f)).patternData]),
  );
  /** @type {Record<string, { wings: number[]; midge: number }>} */
  const slots = {};
  for (const orbit of midgeOrbit ? [wingOrbit, midgeOrbit] : [wingOrbit]) {
    const home = solved.patternData[orbit];
    for (let i = 0; i < home.pieces.length; i++) {
      const sig = EDGE_FACES.filter(
        (f) =>
          turned[f][orbit].pieces[i] !== home.pieces[i] ||
          turned[f][orbit].orientation[i] !== home.orientation[i],
      )
        .sort()
        .join("");
      slots[sig] ??= { wings: [], midge: -1 };
      if (orbit === wingOrbit) slots[sig].wings.push(i);
      else slots[sig].midge = i;
    }
  }
  return slots;
}

/**
 * The content of one edge position — both wing stickers with their
 * orientations, plus the midge where there is one — as a comparable key.
 *
 * @param {Record<string, { wings: number[]; midge: number }>} slots
 * @param {{ wingOrbit?: string; midgeOrbit?: string | null }} [opts]
 * @returns {(pattern: any, signature: string) => string}
 */
export function makeArrangementKey(slots, { wingOrbit = "EDGES", midgeOrbit = null } = {}) {
  return (pattern, signature) => {
    const { wings, midge } = slots[signature];
    const w = pattern.patternData[wingOrbit];
    const parts = [wings.map((i) => [w.pieces[i], w.orientation[i]])];
    if (midgeOrbit) {
      const m = pattern.patternData[midgeOrbit];
      parts.push(m.pieces[midge], m.orientation[midge]);
    }
    return JSON.stringify(parts);
  };
}

/**
 * Every arrangement of every edge position that is an INTACT group, calibrated
 * from the 24 whole-cube rotations rather than declared.
 *
 * A group carried to another position, or turned over as a unit, is still
 * intact; a position whose two wings belong to different edges is not. This is
 * the property that means "the reduction survived" — and on the 4x4 it is what
 * "the parity is gone" is checked with.
 *
 * @param {any} solved
 * @param {any[]} ROTATION_T
 * @param {Record<string, { wings: number[]; midge: number }>} slots
 * @param {(pattern: any, signature: string) => string} arrKey
 * @returns {Record<string, Set<string>>} signature -> the arrangements it may hold
 */
export function intactArrangements(solved, ROTATION_T, slots, arrKey) {
  /** @type {Record<string, Set<string>>} */
  const valid = {};
  for (const sig of Object.keys(slots)) valid[sig] = new Set();
  for (const r of ROTATION_T) {
    const p = solved.applyTransformation(r);
    for (const sig of Object.keys(slots)) valid[sig].add(arrKey(p, sig));
  }
  return valid;
}

/**
 * Permutation parity of one orbit: 0 even, 1 odd.
 *
 * A permutation of n elements in c cycles is even iff n - c is even. Read
 * against `solved`'s own piece ids rather than assuming they are 0..n-1, so it
 * does not depend on how cubing.js happens to number an orbit.
 *
 * @param {any} pattern
 * @param {any} solved
 * @param {string} [orbit]
 * @returns {number} 0 (even) or 1 (odd)
 */
export function permutationParity(pattern, solved, orbit = "EDGES") {
  const home = solved.patternData[orbit].pieces;
  const to = pattern.patternData[orbit].pieces.map((/** @type {number} */ v) => home.indexOf(v));
  const seen = new Array(to.length).fill(false);
  let cycles = 0;
  for (let i = 0; i < to.length; i++) {
    if (seen[i]) continue;
    cycles++;
    for (let j = i; !seen[j]; j = to[j]) seen[j] = true;
  }
  return (to.length - cycles) % 2;
}
