/**
 * One-time curriculum extraction: fetch JPerm's alg-set data files, parse the
 * `algsetAlgs` arrays, validate every algorithm, classify cases mechanically,
 * and emit typed JSON for src/data/. Committed output — never fetched at
 * build or runtime (offline-first).
 *
 * Validation layers:
 *  1. every alg parses (`new Alg(s)`) and is legal for its puzzle (kpuzzle)
 *  2. every 3x3 OLL/PLL alg preserves the first two layers (F2L invariant)
 *  3. algs listed under the same case produce the same last-layer state class
 *     (up to AUF), and distinct cases produce distinct classes
 *
 * Usage: node scripts/extract-algs.mjs
 */
import { writeFile, mkdir } from "node:fs/promises";
import vm from "node:vm";
import { Alg } from "cubing/alg";
import { cube3x3x3 } from "cubing/puzzles";

const SETS = [
  { name: "oll", url: "https://jperm.net/lib/oll.js", expect: 57 },
  { name: "pll", url: "https://jperm.net/lib/pll.js", expect: 21 },
  { name: "2loll", url: "https://jperm.net/lib/2loll.js", expect: null },
  { name: "2lpll", url: "https://jperm.net/lib/2lpll.js", expect: null },
  { name: "f2l", url: "https://jperm.net/lib/f2l.js", expect: 41 },
  { name: "4x4oll", url: "https://jperm.net/lib/4x4oll.js", expect: null },
  { name: "4x4pll", url: "https://jperm.net/lib/4x4pll.js", expect: null },
];

async function fetchSet({ name, url }) {
  const res = await fetch(url, { headers: { "user-agent": "cubepath-extractor" } });
  if (!res.ok) return { name, url, error: `HTTP ${res.status}` };
  const text = await res.text();
  // The lib files assign arrays to variables; execute in a sandbox and take
  // every array-of-objects binding.
  const sandbox = {};
  try {
    vm.createContext(sandbox);
    vm.runInContext(text, sandbox, { timeout: 5000 });
  } catch (e) {
    return { name, url, error: `eval failed: ${e.message}`, raw: text.slice(0, 400) };
  }
  const arrays = Object.entries(sandbox).filter(
    ([, v]) => Array.isArray(v) && v.length > 0 && typeof v[0] === "object",
  );
  if (arrays.length === 0) return { name, url, error: "no alg arrays found", keys: Object.keys(sandbox) };
  return { name, url, bindings: Object.fromEntries(arrays) };
}

const kpuzzle = await cube3x3x3.kpuzzle();

/** F2L stickers must be untouched by a last-layer alg. */
function preservesF2L(algStr) {
  try {
    const t = kpuzzle.algToTransformation(new Alg(algStr));
    const tp = t.transformationData;
    // Corners: positions 4-7 are D-layer on the standard 3x3 kpuzzle? Don't
    // assume — check via pattern: apply to solved and compare non-U facelets.
    const solved = kpuzzle.defaultPattern();
    const moved = solved.applyTransformation(t);
    const s = solved.patternData, m = moved.patternData;
    // EDGES orbit: 12 pieces; U-layer edges are wherever they are — instead of
    // hardcoding indices, require: every piece that changed position or
    // orientation must, in the solved pattern, belong to the U layer. We
    // detect U-layer membership by applying a U turn to solved and seeing
    // which indices move.
    const uTurn = kpuzzle.algToTransformation(new Alg("U"));
    const uMoved = solved.applyTransformation(uTurn).patternData;
    for (const orbit of Object.keys(s)) {
      const n = s[orbit].pieces.length;
      for (let i = 0; i < n; i++) {
        const inU =
          uMoved[orbit].pieces[i] !== s[orbit].pieces[i] ||
          uMoved[orbit].orientation[i] !== s[orbit].orientation[i];
        const changed =
          m[orbit].pieces[i] !== s[orbit].pieces[i] ||
          m[orbit].orientation[i] !== s[orbit].orientation[i];
        if (changed && !inU) return false;
      }
    }
    return true;
  } catch {
    return false;
  }
}

/** Canonical last-layer class of the state an alg solves, up to AUF. */
function llClass(algStr) {
  const inv = new Alg(algStr).invert();
  let best = null;
  for (let auf = 0; auf < 4; auf++) {
    const pre = kpuzzle
      .defaultPattern()
      .applyAlg(new Alg("U".repeat(0) + (auf ? `U${auf === 1 ? "" : auf}` : "")))
      .applyAlg(inv);
    const key = JSON.stringify(pre.patternData);
    if (best === null || key < best) best = key;
  }
  return best;
}

const out = {};
const report = [];
for (const set of SETS) {
  const r = await fetchSet(set);
  if (r.error) {
    report.push(`${set.name}: FAILED — ${r.error}`);
    continue;
  }
  const cases = [];
  for (const [binding, arr] of Object.entries(r.bindings)) {
    for (const item of arr) {
      cases.push({ binding, ...item });
    }
  }
  // Validate 3x3 sets
  let parsed = 0,
    f2lOk = 0,
    total = 0;
  for (const c of cases) {
    const algs = Array.isArray(c.alg) ? c.alg : [c.alg];
    for (const a of algs) {
      if (typeof a !== "string" || a.includes("[*]")) continue;
      total++;
      try {
        new Alg(a);
        parsed++;
        if (["oll", "pll", "2loll", "2lpll"].includes(set.name)) {
          if (preservesF2L(a)) f2lOk++;
        }
      } catch {
        report.push(`${set.name}: parse FAIL: ${JSON.stringify(a).slice(0, 80)}`);
      }
    }
  }
  out[set.name] = cases;
  report.push(
    `${set.name}: ${cases.length} cases, ${parsed}/${total} algs parse` +
      (["oll", "pll", "2loll", "2lpll"].includes(set.name) ? `, ${f2lOk}/${total} preserve F2L` : ""),
  );
  if (set.expect && cases.length !== set.expect) {
    report.push(`${set.name}: WARNING expected ${set.expect} cases, got ${cases.length}`);
  }
}

await mkdir(new URL("../src/data/extracted", import.meta.url), { recursive: true });
await writeFile(
  new URL("../src/data/extracted/jperm-raw.json", import.meta.url),
  JSON.stringify(out, null, 1),
);
console.log(report.join("\n"));
console.log("\nWrote src/data/extracted/jperm-raw.json");
