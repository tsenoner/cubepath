/**
 * Unlockable sets — case data that ships in the repo, verified, but
 * deliberately not surfaced in the UI yet.
 *
 * ┌─ THE SWITCH ────────────────────────────────────────────────────────────┐
 * │ Flip a value in `UNLOCKED` below to `true` and the set reappears        │
 * │ everywhere at once: the trainer's set list, its pool and its counts,    │
 * │ the /reference sections, and the /case/<id> pages. Its DIAGRAMS have to │
 * │ be regenerated first — see below; the build fails without them.         │
 * └─────────────────────────────────────────────────────────────────────────┘
 *
 * Everything else in the app asks `isLocked()`; nothing re-derives the rule.
 * The case DATA is untouched by this file — `src/data/extracted/*.json` and
 * `fullsets*.gen.ts` keep every case, so the algorithm tests keep verifying
 * the hidden algs exactly as before.
 *
 * THE DIAGRAMS ARE THE EXCEPTION, and it is the one second place to edit.
 * The 61 SVGs for these sets were reachable from no page at all and are no
 * longer generated, so an unlocked set has no picture until a diagram group is
 * added back to `fullsets.render_big_sets` (see `TAUGHT_BIG_CUBE` there).
 * Flipping a boolean here restores every other surface; it does not restore
 * the pictures — and the pictures are GATED, so this is not a cosmetic gap:
 * `tests/algs.spec.ts` § "every case a reader can reach has a picture" fails
 * the build for every newly visible case that has no `icon`. Unlocking a set
 * is therefore two edits, in this order: regenerate its diagrams, then flip
 * the boolean. `make check` tells you if you did it the other way round.
 */
import type { CaseDef } from "../data/algs";

export type UnlockKey = "444-parity-embedded" | "555-l2e-onelook";

/**
 * The one line to flip per set. Keep this a plain literal — it is meant to be
 * greppable and obvious, not computed.
 */
export const UNLOCKED: Record<UnlockKey, boolean> = {
  "444-parity-embedded": false,
  "555-l2e-onelook": false,
};

/**
 * The two 4×4 cases the course actually teaches, and the only 4×4 cases the UI
 * shows while `444-parity-embedded` is locked.
 *
 * These are exactly the two big-cube algorithms J Perm's 4×4 tutorial teaches:
 * `444.oll-parity` is transformation-identical to his OLL parity, and
 * `444.pll.pure-e`'s algorithm *is* the bare PLL-parity string
 * `2R2 U2 2R2 Uw2 2R2 Uw2`, byte for byte.
 *
 * `444.pll.adj-e` used to sit here as "parity's second face". It is the parity
 * algorithm with a U-perm fused around it, and it was verified redundant rather
 * than assumed: running the bare parity algorithm on the Adj-E case leaves a
 * plain Ua, so parity-then-PLL finishes it with algorithms the reader already
 * owns. It bought one look and cost a fourth algorithm — the same trade the 48
 * cases below are locked for, so it is locked on the same rule.
 */
export const TAUGHT_444_CASES: ReadonlySet<string> = new Set(["444.oll-parity", "444.pll.pure-e"]);

/**
 * The one 5×5 case the course teaches: edge parity.
 *
 * The other twelve last-two-edges cases are a one-look optimisation. The
 * course finishes L2E the way J Perm's beginner tutorial does — slice, flip,
 * slice back, repeated — and that is provably enough: every outer-turn
 * algorithm (the flip included) is EVEN on the 24 wings and conjugating by a
 * slice cannot change parity, so no amount of pairing reaches an odd state.
 * The parity algorithm is the one ODD generator, which makes it the second
 * thing a solver must own and the twelve merely faster.
 * `scripts/verify-l2e.mjs` asserts that parity argument; it is not a comment.
 */
export const TAUGHT_555_CASES: ReadonlySet<string> = new Set(["555.l2e-6"]);

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
     * any 4×4, so shipping 48 more cases only offered a beginner a wall of
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
  {
    key: "555-l2e-onelook",
    /*
     * Twelve of the thirteen 5x5 last-two-edges cases, locked for the same
     * reason as the 4x4 set: they are a speed refinement, not the method.
     *
     * Two independent reasons, both true regardless of what is taught. The
     * course needs two algorithms plus one technique to finish any 5x5, and
     * the twelve are none of them. And they were never usable as shipped:
     * gen-cases.mjs gave all thirteen the same hardcoded recognition string
     * and all thirteen are named "L2E 1".."L2E 13", so with no 5x5 diagrams
     * /reference rendered thirteen identically-labelled text tiles that no
     * learner could tell apart, let alone drill.
     *
     * The GROUP stays visible: a one-case trainer set is genuinely useful
     * here, because it drills the only recognition question a 5x5 asks — is
     * this parity, or not? It is keyed `555-parity`, not `555-l2e`, because
     * that is what is left in it once these twelve are hidden. THIS key keeps
     * "l2e" on purpose: it names the SOURCE SET it hides, which really is
     * SpeedCubeDB's L2E set of thirteen.
     */
    reason:
      "one-look last-two-edges cases — a speed refinement; the course finishes L2E with " +
      "slice-flip-slice plus the parity algorithm",
    hidesCase: (def) => def.id.startsWith("555.l2e-") && !TAUGHT_555_CASES.has(def.id),
    hidesGroup: () => false,
  },
];

/**
 * The one predicate. Pass a case (locked by id, so the two taught 4×4 cases
 * stay visible even though one of them sits inside a locked group) or a group
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
