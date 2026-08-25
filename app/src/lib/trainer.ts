/**
 * Trainer logic: case selection, weighted case picking, setup scrambles,
 * and session statistics. Pure functions + a thin idb-settings layer.
 */
import { ALL_CASES, isFullOll, isFullPll, primaryAlg, type CaseDef } from "../data/algs";
import { CASE_SCRAMBLES } from "../data/fullsets.gen";
import { getDB } from "./db";

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

export async function loadSettings(): Promise<TrainerSettings> {
  const db = await getDB();
  const stored = (await db.get("settings", "trainer")) as Partial<TrainerSettings> | undefined;
  return { ...DEFAULT_SETTINGS, ...stored };
}

export async function saveSettings(settings: TrainerSettings): Promise<void> {
  const db = await getDB();
  await db.put("settings", settings, "trainer");
}

/** Trainable sets in course order, with display names and case predicates. */
export const TRAINER_GROUPS: {
  key: string;
  name: string;
  member: (c: CaseDef) => boolean;
}[] = [
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
  { key: "444-oll", name: "4×4 OLL + parity", member: (c) => c.group.startsWith("4x4oll-") },
  { key: "444-pll", name: "4×4 PLL + parity", member: (c) => c.group.startsWith("4x4pll-") },
  { key: "555-l2e", name: "5×5 last two edges", member: (c) => c.group === "555-l2e" },
];

export function groupSize(key: string): number {
  const g = TRAINER_GROUPS.find((t) => t.key === key);
  return g ? ALL_CASES.filter((c) => g.member(c)).length : 0;
}

export function poolFor(groups: string[]): CaseDef[] {
  const members = TRAINER_GROUPS.filter((t) => groups.includes(t.key)).map((t) => t.member);
  const pool = ALL_CASES.filter((c) => members.some((m) => m(c)));
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
