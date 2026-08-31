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

/**
 * The big-cube cases the course TEACHES, and the diagram drawn for each.
 *
 * There are three, and that is the whole big-cube picture budget, because the
 * course teaches REDUCTION: a 4x4 or 5x5 becomes a 3x3 and the 3x3 method
 * finishes it. What is left over is parity — two fixes on the 4x4, one on the
 * 5x5 — and nothing else needs a picture.
 *
 * The other 60 big-cube cases still ship as verified DATA (the parity
 * algorithms are located inside those sets by mechanism rather than retyped),
 * but they are one-look optimisations, `src/lib/unlocks.ts` keeps them out of
 * every surface, and they carry no icon because no diagram is generated for
 * them. `tools/cubepath/src/cubepath/fullsets.py` holds the same three ids as
 * `TAUGHT_BIG_CUBE`, and a Python test asserts the two lists agree.
 *
 * Paths are written out rather than built from the id: three literals a reader
 * can check against `ls app/public/diagrams` beat a string-surgery rule with
 * three inputs, and test_diagrams.py resolves every one of them to a file.
 * @type {Record<string, string>}
 */
const TAUGHT_BIG_CUBE = {
  // KEY-ONLY. This generator never builds the id `444.oll-parity` — it emits
  // `444.oll.<slug>`, `444.pll.<slug>` and `555.<slug>` — because OLL parity is
  // a CURATED case, and src/data/algs.ts owns its icon. The row is here so the
  // three-language gate can compare one list of ids; test_diagrams.py asserts
  // this path against the curated one, so the two literals cannot drift.
  "444.oll-parity": "/diagrams/444-parity/444_oll_parity.svg",
  "444.pll.pure-e": "/diagrams/444-parity/444_pll_pure_e.svg",
  "555.l2e-6": "/diagrams/555-parity/555_l2e_6.svg",
};

/**
 * Case id -> the name to print, where the source's own label is an index or a
 * set-internal code rather than a name a learner can use.
 *
 * Kept deliberately small. A case whose only identity IS its index ("L2E 11",
 * "OLL 33") keeps that index — inventing names for cases nobody names is worse
 * than an index. What is here is the two BIG-CUBE PARITY cases, and they earn
 * it: they are the only two algorithms the 4x4 and 5x5 courses teach, every
 * lesson and every cheat card calls them "OLL parity" and "PLL parity", and
 * the source labels — SpeedCubeDB's positional "L2E 6", JPerm's set-internal
 * "Pure-E" — name neither. `444.pll.pure-e`'s algorithm IS the bare PLL-parity
 * string byte for byte (asserted in tests/algs.spec.ts against
 * case-states.json's `parityAlgs`), and `555.l2e-6` carries J Perm's own
 * 5x5 parity alg, so these are renames, not reclassifications.
 * @type {Record<string, string>}
 */
const NAME_OVERRIDES = {
  "555.l2e-6": "Edge Parity (5×5)",
  "444.pll.pure-e": "PLL Parity (4×4)",
};

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
    icon: `/diagrams/f2l/f2l_${String(c.number).padStart(2, "0")}.svg`,
  });
  if (c.setup) scrambles[id] = [c.setup];
}

for (const c of l2e) {
  const id = `555.${c.slug}`;
  addCase({
    id,
    group: "555-parity",
    name: NAME_OVERRIDES[id] ?? c.name,
    // Every one of the 13 shared this hardcoded string and bypassed the
    // recognition.json lookup the other branches use, so /reference rendered
    // thirteen identically-labelled tiles that no learner could tell apart.
    recognition: recognition[id] ?? "Last two edges (5×5)",
    algs: c.algs,
    stickering: "full",
    puzzle: "5x5x5",
    phase: "555",
    ...(TAUGHT_BIG_CUBE[id] ? { icon: TAUGHT_BIG_CUBE[id] } : {}),
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
      name: NAME_OVERRIDES[id] ?? `${c.name} (4×4 ${setName.includes("oll") ? "OLL" : "PLL"})`,
      // The extraction's group label ("Edges Only", "0 Corners") describes the
      // case, not the representative this repo draws for it — the case state is
      // a bare alg-inverse with no AUF normalisation, so a picture can carry a
      // free U-turn of the corners on top of the thing the label names. Let a
      // hand-written cue win where one exists, exactly as the OLL/PLL branches
      // already do; the group label stays the fallback.
      recognition: recognition[id] ?? `${c.group}`,
      algs: c.algs,
      stickering: "full",
      puzzle: "4x4x4",
      phase,
      ...(TAUGHT_BIG_CUBE[id] ? { icon: TAUGHT_BIG_CUBE[id] } : {}),
    });
    // NO trainer scrambles for the big-cube sets, deliberately. The extraction
    // ships scrambles for these cases, but every one of them is outer-layer
    // moves only — and outer turns carry both wings of an edge together, so
    // from a reduced cube they can never produce either parity. All 196 of them
    // set up an ordinary 3x3-legal state instead of the case they name, which
    // means a learner drilling 4x4 parity never met the case. `setupScramble`
    // falls back to inverse-of-alg with a random AUF, which is correct here.
    // `algs.spec.ts` pins that no big-cube scramble ships.
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
