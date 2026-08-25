/**
 * Shared kpuzzle verification kit for the extraction/verification scripts
 * (extract-algs.mjs, verify-f2l.mjs, verify-l2e.mjs): rotation enumeration,
 * transformation helpers, and rotation-normalization.
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
