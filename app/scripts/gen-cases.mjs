/**
 * Generate the case dataset from the verified extraction
 * (src/data/extracted/*.json + src/data/recognition.json):
 *
 *  - src/data/fullsets.gen.ts — LEAN cases (primary alg only, no recognition)
 *    plus capped trainer scrambles. This file ships to the client via the
 *    practice island, so it carries only what runtime code needs.
 *  - src/data/fullsets.rich.gen.ts — recognition text + alternate algs for
 *    every generated case. Build-time pages only; never shipped.
 *
 * Usage: node scripts/gen-cases.mjs
 */
import { readFile, writeFile } from "node:fs/promises";

/**
 * Shapes of the verified extraction files. JSON.parse returns `any`, so these
 * are what makes the field names below checked rather than assumed.
 *
 * @typedef {{ name: string; group: string; prob?: number; algs: string[]; scrambles: string[] }} RawCase
 * @typedef {Record<"oll" | "pll" | "4x4oll" | "4x4pll", RawCase[]>} RawSets
 * @typedef {{ number: number; name: string; group: string; setup?: string; algs: string[] }} F2LCase
 * @typedef {{ slug: string; name: string; algs: string[] }} L2ECase
 * @typedef {{ id: string; group: string; name: string; recognition: string; algs: string[];
 *   stickering: string; puzzle: string; phase: string; probability?: string; icon?: string }} CaseInput
 */

/** @type {RawSets} */
const raw = JSON.parse(
  await readFile(new URL("../src/data/extracted/jperm-raw.json", import.meta.url), "utf8"),
);
/** @type {Record<string, string>} */
const recognition = JSON.parse(
  await readFile(new URL("../src/data/recognition.json", import.meta.url), "utf8"),
);
/** @type {{ f2l: F2LCase[] }} */
const f2l = JSON.parse(
  await readFile(new URL("../src/data/extracted/f2l-raw.json", import.meta.url), "utf8"),
);
/** @type {L2ECase[]} */
const l2e = JSON.parse(
  await readFile(new URL("../src/data/extracted/l2e-raw.json", import.meta.url), "utf8"),
);

/** @param {string | number} s */
const slug = (s) =>
  String(s)
    .replace(/\+$/, " plus")
    .replace(/-$/, " minus")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

const MAX_SCRAMBLES = 5;

/**
 * Lean alg list: the primary variant only (alternates live in RICH).
 * @param {string[]} algs
 */
const toAlgs = (algs) => [{ moves: algs[0], primary: true }];
/** @param {string[]} algs */
const toAlternates = (algs) => algs.slice(1).map((moves) => ({ moves }));

/** @param {number | undefined} prob */
function ollProbability(prob) {
  // JPerm OLL probs are numerators over 216.
  return prob ? `${prob}/216` : undefined;
}
/** @param {number | undefined} prob */
function pllProbability(prob) {
  // JPerm PLL probs are numerators over 18 (T=1 → 1/18, N=0.25 → 1/72).
  if (!prob) return undefined;
  if (Number.isInteger(prob)) return `${prob}/18`;
  const denom = Math.round(18 / prob);
  return `1/${denom}`;
}

/** @type {Record<string, unknown>[]} */
const cases = [];
/** @type {Record<string, string[]>} */
const scrambles = {};
/** @type {Record<string, { recognition: string; alternates: { moves: string }[] }>} */
const rich = {};

/** @param {CaseInput} input */
function addCase({ id, icon, recognition: rec, algs, ...lean }) {
  cases.push({ id, ...lean, algs: toAlgs(algs), ...(icon ? { icon } : {}) });
  rich[id] = { recognition: rec, alternates: toAlternates(algs) };
}

for (const c of raw.oll) {
  const num = Number(c.name);
  const id = `oll.${num}`;
  addCase({
    id,
    group: `oll-${slug(c.group)}`,
    name: `OLL ${c.name}`,
    recognition: recognition[id] ?? `${c.group} shape`,
    algs: c.algs,
    stickering: "OLL",
    puzzle: "3x3x3",
    probability: ollProbability(c.prob),
    phase: "full-oll",
    icon: `/diagrams/oll-full/oll_${String(num).padStart(2, "0")}.svg`,
  });
  scrambles[id] = c.scrambles.slice(0, MAX_SCRAMBLES);
}

for (const c of raw.pll) {
  const id = `pll.${slug(c.name)}`;
  addCase({
    id,
    group: `pll-${slug(c.group)}`,
    name: `${c.name}-Perm`,
    recognition: recognition[id] ?? c.group,
    algs: c.algs,
    stickering: "PLL",
    puzzle: "3x3x3",
    probability: pllProbability(c.prob),
    phase: "full-pll",
    icon: `/diagrams/pll-full/pll_full_${slug(c.name)}.svg`,
  });
  scrambles[id] = c.scrambles.slice(0, MAX_SCRAMBLES);
}

for (const c of f2l.f2l) {
  if (!c.number) continue;
  const id = `f2l.${c.number}`;
  addCase({
    id,
    group: `f2l-${slug(c.group)}`,
    name: `F2L ${c.number}`,
    recognition: c.group,
    algs: c.algs,
    stickering: "F2L",
    puzzle: "3x3x3",
    phase: "full-f2l",
  });
  if (c.setup) scrambles[id] = [c.setup];
}

for (const c of l2e) {
  addCase({
    id: `555.${c.slug}`,
    group: "555-l2e",
    name: c.name,
    recognition: "Last two edges (5×5)",
    algs: c.algs,
    stickering: "full",
    puzzle: "5x5x5",
    phase: "555",
  });
}

/** @type {["4x4oll" | "4x4pll", string, string][]} */
const BIG_SETS = [
  ["4x4oll", "444.oll", "444"],
  ["4x4pll", "444.pll", "444"],
];
for (const [setName, prefix, phase] of BIG_SETS) {
  for (const c of raw[setName]) {
    const id = `${prefix}.${slug(c.name)}`;
    addCase({
      id,
      group: `${setName}-${slug(c.group)}`,
      name: `${c.name} (4×4 ${setName.includes("oll") ? "OLL" : "PLL"})`,
      recognition: `${c.group}`,
      algs: c.algs,
      stickering: "full",
      puzzle: "4x4x4",
      phase,
    });
    scrambles[id] = c.scrambles.slice(0, MAX_SCRAMBLES);
  }
}

/** @param {string} extra */
const header = (extra) => `/**
 * GENERATED by scripts/gen-cases.mjs from the verified JPerm extraction —
 * do not edit by hand. ${extra}
 */
`;

await writeFile(
  new URL("../src/data/fullsets.gen.ts", import.meta.url),
  header(
    "Lean runtime dataset: primary algs only — recognition and alternates live in fullsets.rich.gen.ts.",
  ) +
    `import type { CaseDef } from "./algs";\n\n` +
    `export const GENERATED_CASES: CaseDef[] = ${JSON.stringify(cases, null, 2)};\n\n` +
    `/** Verified per-case trainer scrambles (each produces its case). */\n` +
    `export const CASE_SCRAMBLES: Record<string, string[]> = ${JSON.stringify(scrambles, null, 2)};\n`,
);

await writeFile(
  new URL("../src/data/fullsets.rich.gen.ts", import.meta.url),
  header(
    "Build-time companion to fullsets.gen.ts: recognition text and alternate algorithms per generated case. Never import from client code.",
  ) +
    `import type { AlgVariant } from "./algs";\n\n` +
    `export const RICH: Record<string, { recognition: string; alternates: AlgVariant[] }> = ` +
    `${JSON.stringify(rich, null, 2)};\n`,
);

console.log(
  `generated ${cases.length} cases (${Object.values(scrambles).flat().length} scrambles, ` +
    `${Object.values(rich).reduce((n, r) => n + r.alternates.length, 0)} rich alternates)`,
);
