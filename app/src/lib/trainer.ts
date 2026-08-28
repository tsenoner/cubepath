/**
 * Trainer logic: case selection, weighted case picking, setup scrambles,
 * and session statistics. Pure functions + a thin idb-settings layer.
 */
import { ALL_CASES, isFullOll, isFullPll, primaryAlg, type CaseDef } from "../data/algs";
import { CASE_SCRAMBLES } from "../data/fullsets.gen";
import { getDB } from "./db";
import { TAUGHT_444_CASES, isLocked } from "./unlocks";

export interface TrainerSettings {
  /** Selected trainer groups (keys of CASES.group). */
  groups: string[];
  /** "realistic" weights by case probability; "balanced" is uniform. */
  frequencies: "realistic" | "balanced";
}

const DEFAULT_SETTINGS: TrainerSettings = {
  groups: ["2look-oll-corners", "2look-pll-corners", "2look-pll-edges"],
  frequencies: "realistic",
};

/** A fresh copy of the default trainer settings (safe to mutate). */
export function defaultSettings(): TrainerSettings {
  return { ...DEFAULT_SETTINGS, groups: [...DEFAULT_SETTINGS.groups] };
}

export async function loadSettings(): Promise<TrainerSettings> {
  const db = await getDB();
  const stored = (await db.get("settings", "trainer")) as Partial<TrainerSettings> | undefined;
  return { ...DEFAULT_SETTINGS, ...stored };
}

export async function saveSettings(settings: TrainerSettings): Promise<void> {
  const db = await getDB();
  await db.put("settings", settings, "trainer");
}

export interface TrainerGroup {
  key: string;
  name: string;
  member: (c: CaseDef) => boolean;
}

/**
 * Every trainable set in course order, **including the ones lib/unlocks.ts is
 * currently hiding**. Locked sets stay defined here so that unlocking is one
 * boolean and not a re-import of deleted code; nothing renders this list
 * directly — `trainerGroups()` below is what the UI sees.
 */
const ALL_TRAINER_GROUPS: TrainerGroup[] = [
  { key: "cross-eo", name: "Yellow cross", member: (c) => c.group === "cross-eo" },
  {
    key: "2look-oll-corners",
    name: "2-Look OLL corners",
    member: (c) => c.group === "2look-oll-corners",
  },
  {
    key: "2look-pll-corners",
    name: "2-Look PLL corners",
    member: (c) => c.group === "2look-pll-corners",
  },
  {
    key: "2look-pll-edges",
    name: "2-Look PLL edges",
    member: (c) => c.group === "2look-pll-edges",
  },
  { key: "full-f2l", name: "F2L (41)", member: (c) => c.phase === "full-f2l" },
  { key: "full-oll", name: "Full OLL (57)", member: isFullOll },
  { key: "full-pll", name: "Full PLL (all 21)", member: isFullPll },
  {
    // What the 4×4 course actually teaches: OLL parity and the two faces of
    // PLL parity. The old "4×4 OLL + parity" / "4×4 PLL + parity" pair read as
    // "the OLL set, plus a parity case"; the contents were the opposite —
    // last-layer cases with the parity fix baked in.
    key: "444-parity",
    name: "4×4 parity",
    member: (c) => TAUGHT_444_CASES.has(c.id),
  },
  // Locked while UNLOCKED["444-parity-embedded"] is false — see lib/unlocks.ts
  // for the measurement and the reason. Defined, drilled by nobody, restored
  // in full the moment the flag flips.
  {
    key: "444-oll",
    name: "4×4 OLL (parity-embedded)",
    member: (c) => c.group.startsWith("4x4oll-"),
  },
  {
    key: "444-pll",
    name: "4×4 PLL (parity-embedded)",
    member: (c) => c.group.startsWith("4x4pll-"),
  },
  { key: "555-l2e", name: "5×5 edge parity", member: (c) => c.group === "555-l2e" },
];

/**
 * The sets the UI may show, filtered live through `isLocked` so that flipping
 * an unlock takes effect without touching anything here.
 */
export function trainerGroups(): TrainerGroup[] {
  return ALL_TRAINER_GROUPS.filter((g) => !isLocked(g.key));
}

/**
 * Build-time snapshot of `trainerGroups()`, kept because `layouts/Lesson.astro`
 * validates every lesson's `practice.groups` against it — a lesson must not be
 * able to deep-link into a locked set. Runtime paths call `trainerGroups()`.
 */
export const TRAINER_GROUPS: readonly TrainerGroup[] = trainerGroups();

/**
 * Short set label for a case — the trainer group's name without its count.
 * Derived from `trainerGroups()` so the placeholder tile shown where a case
 * has no diagram yet cannot drift from the set names in the sidebar.
 */
export function groupLabel(def: CaseDef): string {
  const g = trainerGroups().find((t) => t.member(def));
  return g ? g.name.replace(/\s*\([^)]*\)\s*$/, "") : def.group;
}

/** Members of a visible set, minus anything `isLocked` hides inside it. */
function membersOf(g: TrainerGroup): CaseDef[] {
  return ALL_CASES.filter((c) => g.member(c) && !isLocked(c));
}

export function groupSize(key: string): number {
  const g = trainerGroups().find((t) => t.key === key);
  return g ? membersOf(g).length : 0;
}

/** Every trainable set with its members resolved once, in course order. */
export function trainerSets(): { key: string; name: string; cases: CaseDef[] }[] {
  return trainerGroups().map((g) => ({ key: g.key, name: g.name, cases: membersOf(g) }));
}

/**
 * Group keys named by a `?group=` deep link — the handoff every lesson uses to
 * send a reader straight into the set it just taught
 * (`/practice/?group=2look-pll-edges`, comma-separated for more than one).
 *
 * Unknown keys are dropped rather than thrown: a stale link printed on a card
 * or bookmarked from an older build must land on a working trainer, not an
 * empty pool. Order and duplicates are normalised so the stored settings look
 * the same whether they came from a link or from the checkboxes.
 */
export function parseGroupParam(raw: string | null | undefined): string[] {
  if (!raw) return [];
  const known = new Set(trainerGroups().map((g) => g.key));
  const chosen = new Set(
    raw
      .split(",")
      .map((k) => k.trim())
      .filter((k) => known.has(k)),
  );
  // Emit in course order so "full-pll,cross-eo" and "cross-eo,full-pll"
  // produce identical settings.
  return trainerGroups()
    .map((g) => g.key)
    .filter((k) => chosen.has(k));
}

/**
 * One line naming what is selected, for the panel headers — the only place the
 * active set is visible once the panels are collapsed on a phone.
 */
export function selectionLabel(groups: string[]): string {
  const chosen = trainerGroups().filter((g) => groups.includes(g.key));
  if (chosen.length === 0) return "none selected";
  const n = poolFor(groups).length;
  const cases = `${n} case${n === 1 ? "" : "s"}`;
  return chosen.length === 1 ? `${chosen[0]!.name} · ${cases}` : `${chosen.length} sets · ${cases}`;
}

export function poolFor(groups: string[]): CaseDef[] {
  const members = trainerGroups()
    .filter((t) => groups.includes(t.key))
    .map((t) => t.member);
  // Two independent gates, deliberately: a locked *set* cannot be named (its
  // key is not in `trainerGroups()`), and a locked *case* cannot be drilled
  // even if a visible set's predicate happens to cover it.
  const pool = ALL_CASES.filter((c) => !isLocked(c) && members.some((m) => m(c)));
  // The 2-look sets overlap with the full sets by id — dedupe.
  return [...new Map(pool.map((c) => [c.id, c])).values()];
}

function probabilityWeight(def: CaseDef): number {
  if (!def.probability) return 1;
  const [num, den] = def.probability.split("/").map(Number);
  return num && den ? num / den : 1;
}

/** Pick the next case; avoids immediate repeats when the pool allows it. */
export function pickCase(
  pool: CaseDef[],
  mode: TrainerSettings["frequencies"],
  lastId: string | undefined,
  random: () => number = Math.random,
): CaseDef {
  if (pool.length === 0) throw new Error("empty trainer pool");
  const candidates = pool.length > 1 ? pool.filter((c) => c.id !== lastId) : pool;
  if (mode === "balanced") {
    return candidates[Math.floor(random() * candidates.length)]!;
  }
  const weights = candidates.map(probabilityWeight);
  const total = weights.reduce((a, b) => a + b, 0);
  let roll = random() * total;
  for (let i = 0; i < candidates.length; i++) {
    roll -= weights[i]!;
    if (roll <= 0) return candidates[i]!;
  }
  return candidates[candidates.length - 1]!;
}

const AUFS = ["", "U ", "U2 ", "U' "];

/**
 * Invert a plain move sequence: reverse the tokens and toggle the trailing
 * prime (tokens ending in 2 are self-inverse). Only the scramble-pool
 * fallback cases (eo.*, 555.*, 444.oll-parity) reach this, and none of their
 * primary algorithms use parentheses or repeat notation — this stays true by
 * construction, so the heavy cubing/alg parser is not needed here.
 */
function invertMoves(moves: string): string {
  return moves
    .trim()
    .split(/\s+/)
    .reverse()
    .map((t) => (t.endsWith("'") ? t.slice(0, -1) : t.endsWith("2") ? t : `${t}'`))
    .join(" ");
}

/**
 * Setup scramble for a case: prefer the verified per-case scramble pool
 * (varied U-layer permutations); fall back to inverse-of-alg with random AUFs.
 */
export function setupScramble(def: CaseDef, random: () => number = Math.random): string {
  const pool = CASE_SCRAMBLES[def.id];
  if (pool && pool.length > 0) {
    return pool[Math.floor(random() * pool.length)]!;
  }
  const inv = invertMoves(primaryAlg(def));
  const pre = AUFS[Math.floor(random() * 4)]!;
  const post = AUFS[Math.floor(random() * 4)]!;
  return `${pre}${inv} ${post}`.replace(/\s+/g, " ").trim();
}

// ── Session stats ─────────────────────────────────────────────────────

/** Average-of-N with best and worst dropped (standard WCA-style trimming). */
export function averageOf(times: number[], n: number): number | null {
  if (times.length < n) return null;
  const window = times.slice(-n).toSorted((a, b) => a - b);
  const trimmed = window.slice(1, -1);
  return trimmed.reduce((a, b) => a + b, 0) / trimmed.length;
}

export function formatTime(ms: number): string {
  return (ms / 1000).toFixed(2);
}
