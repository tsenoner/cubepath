/**
 * Type declarations for kpuzzle-utils.mjs (the implementation stays plain
 * ESM so the node verify scripts can run it without a build step).
 */
import type { Alg } from "cubing/alg";
import type { KPattern, KPuzzle, KTransformation } from "cubing/kpuzzle";

/** All 24 whole-cube orientations as rotation strings ("" = identity). */
export declare const ROTATIONS: string[];

export interface Kit {
  solved: KPattern;
  ID: KTransformation;
  /** Parse an alg string to a transformation ("" = identity); throws on illegal moves. */
  toT(s: string): KTransformation;
  ROTATION_ALGS: (Alg | null)[];
  ROTATION_T: KTransformation[];
  /** Identity, U, U2, U' as transformations. */
  AUF_T: KTransformation[];
  centersSolved(pattern: KPattern): boolean;
  normalizePattern(pattern: KPattern): KPattern;
  rightRotNormalize(t: KTransformation): KTransformation;
  leftRotNormalize(t: KTransformation): KTransformation;
}

export declare function makeKit(kpuzzle: KPuzzle, opts?: { centerOrbits?: string[] }): Kit;

export interface SlotKit extends Kit {
  U_SLOTS: Record<string, boolean[]>;
  FR_SLOTS: Record<string, boolean[]>;
  FR_PIECE: Record<string, number>;
  outsideSolved(pattern: KPattern, opts: { allowFRSlot: boolean }): boolean;
  uLayerOriented(pattern: KPattern): boolean;
}

export declare function makeSlotKit(kpuzzle: KPuzzle, kit?: Kit): SlotKit;

/**
 * A copy of a pattern's data whose orbits share no arrays.
 *
 * `structuredClone` is NOT safe: cubing.js gives every orbit of the same length
 * the SAME zero-filled orientation array, and a clone preserves that aliasing.
 * See the implementation's comment for the bug it caused.
 */
export declare function unaliasedCopy(
  data: Record<string, { pieces: number[]; orientation: number[] }>,
): Record<string, { pieces: number[]; orientation: number[] }>;
