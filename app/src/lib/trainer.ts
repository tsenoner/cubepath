/**
 * Trainer logic: case selection, weighted case picking, setup scrambles,
 * and session statistics. Pure functions + a thin idb-settings layer.
 */
import { Alg } from "cubing/alg";

import { CASES, primaryAlg, type CaseDef } from "../data/algs";
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

/** Trainable groups in course order, with display names. */
export const TRAINER_GROUPS: { key: string; name: string }[] = [
  { key: "cross-eo", name: "Yellow cross" },
  { key: "2look-oll-corners", name: "2-Look OLL corners" },
  { key: "2look-pll-corners", name: "2-Look PLL corners" },
  { key: "2look-pll-edges", name: "2-Look PLL edges" },
];

export function poolFor(groups: string[]): CaseDef[] {
  const keys = new Set(groups);
  return CASES.filter((c) => keys.has(c.group) && c.puzzle === "3x3x3");
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

/** Setup scramble: random AUF + inverse of the case's algorithm + random AUF. */
export function setupScramble(def: CaseDef, random: () => number = Math.random): string {
  const inv = new Alg(primaryAlg(def)).invert().toString();
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
