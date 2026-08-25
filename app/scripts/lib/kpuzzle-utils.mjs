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
