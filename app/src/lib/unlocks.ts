/**
 * Unlockable sets — case data that ships in the repo, verified and diagrammed,
 * but is deliberately not surfaced in the UI yet.
 *
 * ┌─ THE SWITCH ────────────────────────────────────────────────────────────┐
 * │ Flip a value in `UNLOCKED` below to `true` and the set reappears        │
 * │ everywhere at once: the trainer's set list, its pool and its counts,    │
 * │ the /reference sections, and the /case/<id> pages. That is the whole    │
 * │ change — there is no second place to edit.                              │
 * └─────────────────────────────────────────────────────────────────────────┘
 *
 * Everything else in the app asks `isLocked()`; nothing re-derives the rule.
 * The data itself is untouched by this file — `src/data/extracted/*.json`,
 * `fullsets*.gen.ts` and the generated diagrams all keep every case, so
 * unlocking needs no regeneration and the algorithm tests keep verifying the
 * hidden algs exactly as before.
 */
import type { CaseDef } from "../data/algs";

export type UnlockKey = "444-parity-embedded";

/**
 * The one line to flip per set. Keep this a plain literal — it is meant to be
 * greppable and obvious, not computed.
 */
export const UNLOCKED: Record<UnlockKey, boolean> = {
  "444-parity-embedded": false,
};

/**
 * The three 4×4 cases the course actually teaches, and the only 4×4 cases the
 * UI shows while `444-parity-embedded` is locked.
 *
 * `444.pll.pure-e`'s algorithm *is* the bare PLL-parity algorithm, and the 4×4
 * lesson teaches `444.pll.adj-e` as parity's second face, so both belong to the
 * course even though they were generated alongside the locked set.
 */
export const TAUGHT_444_CASES: ReadonlySet<string> = new Set([
  "444.oll-parity",
  "444.pll.pure-e",
  "444.pll.adj-e",
]);

interface Unlockable {
  key: UnlockKey;
  /** Why the set is hidden. Kept next to the rule so it cannot be lost. */
  reason: string;
  /** True for a case this set hides while locked. */
  hidesCase: (def: CaseDef) => boolean;
  /**
   * True for a group key this set hides while locked — both data group keys
   * (`CaseDef.group`, e.g. "4x4pll-edges-only") and the trainer/reference set
   * keys built on them ("444-oll", "444-pll").
   */
  hidesGroup: (key: string) => boolean;
}

const UNLOCKABLES: readonly Unlockable[] = [
  {
    key: "444-parity-embedded",
    /*
     * Measured, not assumed (scripts/extract-algs.mjs is the source, and the
     * counts are reproducible from src/data/extracted/jperm-raw.json):
     * 27 of 27 `4x4oll` algorithms contain the OLL-parity algorithm verbatim,
     * and 22 of 22 `4x4pll` algorithms contain the PLL-parity algorithm
     * verbatim. They are not a separate 4×4 OLL/PLL system — each one is a
     * last-layer algorithm you already know with the parity fix spliced into
     * it, a one-look optimisation for solvers who already have full OLL/PLL.
     *
     * The course teaches 2-look OLL + PLL plus the parity fixes, which finishes
     * any 4×4, so shipping 47 more cases only offered a beginner a wall of
     * near-duplicates. Locked rather than deleted: the data stays verified and
     * diagrammed, ready to be offered later as a speed refinement.
     * See docs/DECISIONS.md § "4×4 parity-embedded cases".
     */
    reason: "parity-embedded 4×4 last-layer cases — a speed refinement, not part of the course",
    hidesCase: (def) =>
      (def.id.startsWith("444.oll.") || def.id.startsWith("444.pll.")) &&
      !TAUGHT_444_CASES.has(def.id),
    hidesGroup: (key) =>
      key.startsWith("4x4oll-") ||
      key.startsWith("4x4pll-") ||
      key === "444-oll" ||
      key === "444-pll",
  },
];

/**
 * The one predicate. Pass a case (locked by id, so the three taught 4×4 cases
 * stay visible even though two of them sit inside a locked group) or a group
 * key (a `CaseDef.group`, or a trainer/reference set key).
 */
export function isLocked(subject: CaseDef | string): boolean {
  return UNLOCKABLES.some((u) => {
    if (UNLOCKED[u.key]) return false;
    return typeof subject === "string" ? u.hidesGroup(subject) : u.hidesCase(subject);
  });
}

/** Human-readable reason a set is hidden, for docs and error messages. */
export function lockReason(key: UnlockKey): string {
  return UNLOCKABLES.find((u) => u.key === key)?.reason ?? key;
}
