/**
 * One-time curriculum extraction: fetch JPerm's alg-set data files, parse the
 * `algsetAlgs` + `algsetScrambles` arrays, validate every algorithm, verify
 * case-class consistency mechanically, and emit typed JSON for src/data/.
 * Committed output — never fetched at build or runtime (offline-first).
 *
 * Validation layers (3×3 sets):
 *  1. every alg parses (`new Alg(s)`) and is legal on the 3x3 kpuzzle
 *  2. every OLL/PLL alg preserves the first two layers (rotation-normalized)
 *  3. all algs of one case solve the same last-layer state class (up to AUF),
 *     and distinct cases have distinct classes
 *
 * Usage: node scripts/extract-algs.mjs
 */
import { writeFile, mkdir } from "node:fs/promises";
import vm from "node:vm";
import { Alg } from "cubing/alg";
import { cube3x3x3 } from "cubing/puzzles";

const SETS = [
  { name: "oll", url: "https://jperm.net/lib/oll.js", expect: 57, verify: true },
  { name: "pll", url: "https://jperm.net/lib/pll.js", expect: 21, verify: true },
  { name: "4x4oll", url: "https://jperm.net/lib/4x4oll.js", expect: null, verify: false },
  { name: "4x4pll", url: "https://jperm.net/lib/4x4pll.js", expect: null, verify: false },
];

const kpuzzle = await cube3x3x3.kpuzzle();
const solved = kpuzzle.defaultPattern();

// All 24 cube orientations as rotation algs.
const ROTATIONS = [];
for (const a of ["", "x", "x2", "x'", "z", "z'"]) {
  for (const b of ["", "y", "y2", "y'"]) {
    ROTATIONS.push([a, b].filter(Boolean).join(" "));
  }
}

function centersSolved(pattern) {
  // Center ORIENTATION is invisible on a standard cube (picture cubes aside):
  // slice moves twist fixed centers, so compare piece positions only.
  const c = pattern.patternData.CENTERS;
  const s = solved.patternData.CENTERS;
  return c.pieces.every((p, i) => p === s.pieces[i]);
}

/** Rotate a pattern so its centers are solved; null if impossible. */
function normalizeOrientation(pattern) {
  for (const r of ROTATIONS) {
    const p = r ? pattern.applyAlg(new Alg(r)) : pattern;
    if (centersSolved(p)) return p;
  }
  return null;
}

// Which piece slots belong to the U layer (detected, not hardcoded).
const uTurn = solved.applyAlg(new Alg("U")).patternData;
const U_SLOTS = {};
for (const orbit of Object.keys(solved.patternData)) {
  const s = solved.patternData[orbit];
  U_SLOTS[orbit] = s.pieces.map(
    (_, i) =>
      uTurn[orbit].pieces[i] !== s.pieces[i] || uTurn[orbit].orientation[i] !== s.orientation[i],
  );
}

/** A last-layer alg must leave every non-U-layer piece solved (after rotation-normalizing). */
function preservesF2L(algStr) {
  let pattern;
  try {
    pattern = solved.applyAlg(new Alg(algStr));
  } catch {
    return false;
  }
  const p = normalizeOrientation(pattern);
  if (!p) return false;
  const d = p.patternData;
  for (const orbit of Object.keys(d)) {
    const s = solved.patternData[orbit];
    const skipOri = orbit === "CENTERS";
    for (let i = 0; i < s.pieces.length; i++) {
      if (U_SLOTS[orbit][i]) continue;
      if (d[orbit].pieces[i] !== s.pieces[i]) return false;
      if (!skipOri && d[orbit].orientation[i] !== s.orientation[i]) return false;
    }
  }
  return true;
}

/**
 * Canonical class of the state an alg solves, up to: AUF on either side,
 * whole-cube orientation, and y-conjugation (an alternate written for a
 * different holding angle solves y^k ∘ state ∘ y^-k). For OLL sets the class
 * ignores U-layer permutation (OLL algs orient; they may permute freely).
 */
const AUFS = ["", "U", "U2", "U'"];
const YCONJ = [["", ""], ["y", "y'"], ["y2", "y2"], ["y'", "y"]];
function caseClass(algStr, { orientationOnly = false } = {}) {
  const inv = new Alg(algStr).invert().toString();
  const keys = [];
  for (const [yk, ykInv] of YCONJ) {
    for (const pre of AUFS) {
      for (const post of AUFS) {
        const seq = [yk, pre, inv, post, ykInv].filter(Boolean).join(" ");
        const s = solved.applyAlg(new Alg(seq));
        const n = normalizeOrientation(s);
        const data = structuredClone((n ?? s).patternData);
        data.CENTERS.orientation = data.CENTERS.orientation.map(() => 0);
        if (orientationOnly) {
          for (const orbit of Object.keys(data)) {
            data[orbit].pieces = data[orbit].pieces.map((piece, i) =>
              U_SLOTS[orbit][i] ? 0 : piece,
            );
          }
        }
        keys.push(JSON.stringify(data));
      }
    }
  }
  keys.sort();
  return keys[0];
}

async function fetchBindings(url) {
  const res = await fetch(url, { headers: { "user-agent": "cubepath-extractor" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(await res.text(), sandbox, { timeout: 5000 });
  return sandbox;
}

const out = {};
const report = [];
let failures = 0;

for (const set of SETS) {
  let bindings;
  try {
    bindings = await fetchBindings(set.url);
  } catch (e) {
    report.push(`${set.name}: FETCH FAILED — ${e.message}`);
    failures++;
    continue;
  }
  const algs = bindings.algsetAlgs ?? [];
  const scrambles = bindings.algsetScrambles ?? [];
  const cases = algs.map((c, i) => ({
    name: String(c.name),
    group: c.group ?? null,
    prob: c.prob ?? null,
    algs: (Array.isArray(c.alg) ? c.alg : [c.alg]).filter((a) => typeof a === "string"),
    scrambles: scrambles[i] ? Object.values(scrambles[i]).filter((s) => typeof s === "string") : [],
    ...(c.arrows ? { arrows: c.arrows } : {}),
  }));

  if (set.verify) {
    const classes = new Map();
    for (const c of cases) {
      let cls = null;
      for (const a of c.algs) {
        if (!preservesF2L(a)) {
          report.push(`${set.name} ${c.name}: alg breaks F2L: ${a}`);
          failures++;
          continue;
        }
        const k = caseClass(a, { orientationOnly: set.name.includes("oll") });
        if (cls === null) cls = k;
        else if (k !== cls) {
          report.push(`${set.name} ${c.name}: algs disagree on case class`);
          failures++;
        }
      }
      if (cls !== null) {
        if (classes.has(cls)) {
          report.push(`${set.name}: ${c.name} duplicates case of ${classes.get(cls)}`);
          failures++;
        }
        classes.set(cls, c.name);
      }
    }
    report.push(`${set.name}: ${cases.length} cases, ${classes.size} distinct case classes ✓`);
  } else {
    report.push(`${set.name}: ${cases.length} cases (4x4 — verified later on the 4x4 kpuzzle)`);
  }
  if (set.expect && cases.length !== set.expect) {
    report.push(`${set.name}: WARNING expected ${set.expect}, got ${cases.length}`);
    failures++;
  }
  out[set.name] = cases;
}

await mkdir(new URL("../src/data/extracted", import.meta.url), { recursive: true });
await writeFile(
  new URL("../src/data/extracted/jperm-raw.json", import.meta.url),
  JSON.stringify(out, null, 1),
);
console.log(report.join("\n"));
console.log(`\nWrote src/data/extracted/jperm-raw.json (${failures} failures)`);
if (failures > 0) process.exitCode = 1;
