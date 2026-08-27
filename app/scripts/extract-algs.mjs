/**
 * One-time curriculum extraction: fetch JPerm's alg-set data files, parse the
 * `algsetAlgs` + `algsetScrambles` arrays, validate every algorithm and
 * scramble, verify case-class consistency mechanically, and emit typed JSON
 * for src/data/. Committed output — never fetched at build or runtime
 * (offline-first). The JSON is written only when validation is fully clean;
 * on any failure the report prints and the committed file is left untouched.
 *
 * Validation layers — 3×3 sets (oll, pll):
 *  1. every alg parses (`new Alg(s)`) and is legal on the 3x3 kpuzzle
 *  2. every alg preserves the first two layers (rotation-normalized)
 *  3. all algs of one case solve the same case class (up to AUF), and
 *     distinct cases have distinct classes — classBy "orientation" (OLL:
 *     U-layer permutation is free) or "full" (PLL: exact state)
 *  4. every scramble parses and produces its case: scramble (+ optional AUF —
 *     a case is an AUF-equivalence class, and a handful of JPerm scrambles
 *     present the case pre-rotated) + primary alg lands in the identity
 *     class under the set's classBy
 *
 * 4×4 sets (4x4oll, 4x4pll):
 *  1. the file's `specialAlg` matches the parity alg pinned by
 *     docs/research/tech-brief.md §8, and every `[*]` placeholder is expanded
 *     with it — each lib file declares its own: 4x4oll → OLL parity,
 *     4x4pll → PLL parity (a case whose alg is just "[*]" IS "apply parity")
 *  2. after expansion, every alg parses and is legal on the 4x4 kpuzzle
 *     (M/M'/M2 → SiGN m/m'/m2; see translate4x4Slices)
 *  3. every scramble parses and is legal on the 4x4 kpuzzle
 *  TODO(M3): full 4x4 case-class + scramble-produces-case checks on the
 *  4x4 kpuzzle (needs an orientation-mask class model for 4x4 OLL).
 *
 * Usage: node scripts/extract-algs.mjs
 */
import { mkdir, writeFile } from "node:fs/promises";
import vm from "node:vm";
import { Alg } from "cubing/alg";
import { cube3x3x3, puzzles } from "cubing/puzzles";

import { makeKit } from "./lib/kpuzzle-utils.mjs";

/**
 * What a JPerm `lib/*.js` file binds once evaluated in the sandbox. Everything
 * here comes off the network, so the shape is asserted below, never assumed.
 *
 * @typedef {{ name: string | number; group?: string; prob?: number;
 *   alg: string | string[]; arrows?: unknown }} JPermCase
 * @typedef {{ algsetAlgs?: JPermCase[]; algsetScrambles?: unknown[]; specialAlg?: string }} JPermBindings
 */

/** Narrow a `catch` binding to a printable message. @param {unknown} e */
const errText = (e) => (e instanceof Error ? e.message : String(e));

// Parity algs pinned by docs/research/tech-brief.md §8 (jperm.net/4x4 verbatim).
const OLL_PARITY = "Rw U2 x Rw U2 Rw U2 Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'";
const PLL_PARITY = "2R2 U2 2R2 Uw2 2R2 Uw2";

// classBy: how a 3x3 case's class is computed — "orientation" (OLL) or "full"
// (PLL). 4x4 sets carry `parity` (their `[*]` expansion, cross-checked against
// the file's own `specialAlg`) instead and get parse/legality checks only.
const SETS = [
  { name: "oll", url: "https://jperm.net/lib/oll.js", expect: 57, classBy: "orientation" },
  { name: "pll", url: "https://jperm.net/lib/pll.js", expect: 21, classBy: "full" },
  { name: "4x4oll", url: "https://jperm.net/lib/4x4oll.js", expect: 27, parity: OLL_PARITY },
  { name: "4x4pll", url: "https://jperm.net/lib/4x4pll.js", expect: 22, parity: PLL_PARITY },
];

const kpuzzle = await cube3x3x3.kpuzzle();
const kpuzzle4 = await puzzles["4x4x4"].kpuzzle();

// Shared rotation/normalization kit on the 3x3 kpuzzle. The 3x3 kpuzzle pins
// center orientation (CENTERS orientationMod is all 1s), so the kit's
// pieces-only center comparison is the whole story. Every pattern reachable
// from solved by algs normalizes (centers only ever move as a rigid frame),
// so a normalization failure is an internal bug — the kit throws.
const {
  solved,
  toT: toTransformation,
  AUF_T,
  normalizePattern: normalizeOrientation,
  leftRotNormalize,
} = makeKit(kpuzzle);

// Which piece slots belong to the U layer (detected, not hardcoded).
const uTurn = solved.applyAlg(new Alg("U")).patternData;
/** @type {Record<string, boolean[]>} */
const U_SLOTS = {};
for (const orbit of Object.keys(solved.patternData)) {
  const s = solved.patternData[orbit];
  U_SLOTS[orbit] = s.pieces.map(
    (_, i) =>
      uTurn[orbit].pieces[i] !== s.pieces[i] || uTurn[orbit].orientation[i] !== s.orientation[i],
  );
}

/**
 * A last-layer alg must leave every non-U-layer piece solved (after rotation-normalizing).
 * @param {string} algStr
 */
function preservesF2L(algStr) {
  const p = normalizeOrientation(solved.applyAlg(new Alg(algStr)));
  const d = p.patternData;
  for (const orbit of Object.keys(d)) {
    const s = solved.patternData[orbit];
    for (let i = 0; i < s.pieces.length; i++) {
      if (U_SLOTS[orbit][i]) continue;
      if (d[orbit].pieces[i] !== s.pieces[i]) return false;
      if (d[orbit].orientation[i] !== s.orientation[i]) return false;
    }
  }
  return true;
}

/**
 * Canonical class of the state an alg solves, up to: AUF on either side,
 * whole-cube orientation, and y-conjugation (an alternate written for a
 * different holding angle solves y^k ∘ state ∘ y^-k). For OLL sets the class
 * ignores U-layer permutation (OLL algs orient; they may permute freely).
 *
 * Frame correctness: kpuzzle moves act in the fixed spatial frame, so an alg
 * with a NET ROTATION (leading x/y/z, unbalanced wide moves) has
 * pattern(A) = Pure ∘ Rot — but pattern(A⁻¹) = Rot⁻¹ ∘ Pure⁻¹ carries the
 * rotation on the LEFT, where a right-multiplied normalization rotation can
 * only conjugate the state onto the wrong face (and any moves appended after
 * the inverse would turn the wrong physical face). The true case state is
 * S = R ∘ A⁻¹ with the rotation R LEFT-composed so centers are home; AUFs and
 * y-conjugation are then composed around S itself, all in the home frame.
 * Transformation composition is execution order: t1.applyTransformation(t2)
 * means "t1 then t2" (verified: T("R U") ≡ T("R")∘T("U")).
 */
const AUF_ALGS = ["", "U", "U2", "U'"].map((u) => (u ? new Alg(u) : null));
const YCONJ_T = ["", "y", "y2", "y'"].map((y) => {
  const t = toTransformation(y);
  return [t, t.invert()];
});

/**
 * @param {string} algStr
 * @param {{ orientationOnly?: boolean }} [opts]
 */
function caseClass(algStr, { orientationOnly = false } = {}) {
  const S = leftRotNormalize(toTransformation(algStr).invert());
  /** @type {string[]} */
  const keys = [];
  for (const [yk, ykInv] of YCONJ_T) {
    for (const pre of AUF_T) {
      for (const post of AUF_T) {
        // y^k ∘ preAUF ∘ S ∘ postAUF ∘ y^-k — centers stay home throughout.
        const t = yk
          .applyTransformation(pre)
          .applyTransformation(S)
          .applyTransformation(post)
          .applyTransformation(ykInv);
        let data = solved.applyTransformation(t).patternData;
        if (orientationOnly) {
          data = structuredClone(data);
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

/**
 * OLL-solved: every non-U piece home and everything oriented (U permutation free).
 * @param {import("cubing/kpuzzle").KPattern} p
 */
function ollSolvedState(p) {
  const d = p.patternData;
  for (const orbit of Object.keys(d)) {
    const s = solved.patternData[orbit];
    for (let i = 0; i < s.pieces.length; i++) {
      if (d[orbit].orientation[i] !== 0) return false;
      if (!U_SLOTS[orbit][i] && d[orbit].pieces[i] !== s.pieces[i]) return false;
    }
  }
  return true;
}

/** @param {import("cubing/kpuzzle").KPattern} p */
function solvedUpToAUF(p) {
  return AUF_ALGS.some((u) => (u ? p.applyAlg(u) : p).isIdentical(solved));
}

/**
 * A trainer scramble must actually produce its case: scramble (+ optional
 * pre-AUF) followed by the case's primary alg must land in the identity
 * class — fully solved up to a final AUF (classBy "full"), or F2L intact +
 * everything oriented (classBy "orientation": the OLL alg orients, and JPerm's
 * OLL scrambles leave a deliberately random U permutation behind). Whole-cube
 * rotation is normalized away by normalizeOrientation.
 *
 * @param {string} scrambleStr
 * @param {Alg} primaryAlg
 * @param {string | undefined} classBy
 */
function scrambleProducesCase(scrambleStr, primaryAlg, classBy) {
  const scrambled = solved.applyAlg(new Alg(scrambleStr));
  for (const auf of AUF_ALGS) {
    const end = (auf ? scrambled.applyAlg(auf) : scrambled).applyAlg(primaryAlg);
    const p = normalizeOrientation(end);
    if (classBy === "orientation" ? ollSolvedState(p) : solvedUpToAUF(p)) return true;
  }
  return false;
}

/**
 * Why an alg string is unusable on kpuzzle `kp` (parse or legality); null if fine.
 * @param {import("cubing/kpuzzle").KPuzzle} kp
 * @param {string} s
 */
function illegalReason(kp, s) {
  let alg;
  try {
    alg = new Alg(s);
  } catch (e) {
    return `does not parse (${errText(e)})`;
  }
  try {
    kp.algToTransformation(alg);
  } catch (e) {
    return `is illegal (${errText(e)})`;
  }
  return null;
}

/**
 * @param {string} s
 * @param {string} parity
 */
const expandParity = (s, parity) => s.split("[*]").join(parity).replace(/\s+/g, " ").trim();

/**
 * The 4x4 kpuzzle rejects bare M ("Bad grip in move M"): on a 4x4, JPerm's M
 * means the inner two layers. SiGN lowercase `m` is exactly that move with the
 * same direction (verified on the kpuzzle: m ≡ 2-3Rw' ≡ 3Rw' R), so translate
 * M/M'/M2 → m/m'/m2. E and S never appear in the 4x4 sets.
 */
/** @param {string} s */
const translate4x4Slices = (s) => s.replace(/(^|[\s(])M/g, "$1m");

/**
 * @param {string} url
 * @returns {Promise<JPermBindings>}
 */
async function fetchBindings(url) {
  const res = await fetch(url, { headers: { "user-agent": "cubepath-extractor" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  /** @type {JPermBindings} */
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(await res.text(), sandbox, { timeout: 5000 });
  return sandbox;
}

/** @type {Record<string, unknown[]>} */
const out = {};
/** @type {string[]} */
const report = [];
let failures = 0;

for (const set of SETS) {
  let setFailures = 0;
  /** @param {string} msg */
  const fail = (msg) => {
    report.push(`${set.name}: ${msg}`);
    setFailures++;
  };

  let bindings = null;
  try {
    bindings = await fetchBindings(set.url);
  } catch (e) {
    fail(`FETCH FAILED — ${errText(e)}`);
  }
  if (bindings && !(Array.isArray(bindings.algsetAlgs) && bindings.algsetAlgs.length > 0)) {
    fail("fetched file has no algsetAlgs bindings (or they are empty)");
    bindings = null;
  }

  if (bindings) {
    // Non-empty by the Array.isArray guard directly above.
    const rawAlgs = /** @type {JPermCase[]} */ (bindings.algsetAlgs);
    const rawScrambles = bindings.algsetScrambles;
    if (!Array.isArray(rawScrambles) || rawScrambles.length !== rawAlgs.length) {
      fail(
        `algsetScrambles (${Array.isArray(rawScrambles) ? rawScrambles.length : "missing"}) ` +
          `does not match algsetAlgs (${rawAlgs.length}) — scramble join is broken`,
      );
    }
    const cases = rawAlgs.map((/** @type {JPermCase} */ c, /** @type {number} */ i) => {
      const entry = Array.isArray(rawScrambles) ? rawScrambles[i] : undefined;
      if (typeof entry === "string") {
        fail(`${c.name}: scrambles entry is a bare string, not a list`);
      }
      return {
        name: String(c.name),
        group: c.group ?? null,
        prob: c.prob ?? null,
        algs: (Array.isArray(c.alg) ? c.alg : [c.alg]).filter(
          (/** @type {unknown} */ a) => typeof a === "string",
        ),
        scrambles:
          entry && typeof entry === "object"
            ? Object.values(entry).filter((s) => typeof s === "string")
            : [],
        ...(c.arrows ? { arrows: c.arrows } : {}),
      };
    });
    if (cases.length !== set.expect) fail(`expected ${set.expect} cases, got ${cases.length}`);

    let nAlgs = 0;
    let nScrambles = 0;
    if (set.classBy) {
      // 3×3: F2L preservation + case classes + scrambles produce their case.
      const classes = new Map();
      for (const c of cases) {
        if (c.algs.length === 0) {
          fail(`${c.name}: no algorithm strings`);
          continue;
        }
        let cls = null;
        let primaryAlg = null;
        for (const [j, a] of c.algs.entries()) {
          nAlgs++;
          const err = illegalReason(kpuzzle, a);
          if (err) {
            fail(`${c.name}: alg ${err}: ${a}`);
            continue;
          }
          if (j === 0) primaryAlg = new Alg(a);
          if (!preservesF2L(a)) {
            fail(`${c.name}: alg breaks F2L: ${a}`);
            continue;
          }
          const k = caseClass(a, { orientationOnly: set.classBy === "orientation" });
          if (cls === null) cls = k;
          else if (k !== cls) fail(`${c.name}: algs disagree on case class`);
        }
        if (cls !== null) {
          if (classes.has(cls)) fail(`${c.name} duplicates case of ${classes.get(cls)}`);
          classes.set(cls, c.name);
        }
        if (!primaryAlg) {
          fail(`${c.name}: primary alg unusable — scrambles unverifiable`);
          continue;
        }
        for (const s of c.scrambles) {
          nScrambles++;
          const err = illegalReason(kpuzzle, s);
          if (err) fail(`${c.name}: scramble ${err}: ${s}`);
          else if (!scrambleProducesCase(s, primaryAlg, set.classBy)) {
            fail(`${c.name}: scramble does not produce the case: ${s}`);
          }
        }
      }
      if (setFailures === 0) {
        report.push(
          `✓ ${set.name}: ${cases.length} cases, ${classes.size} distinct case classes, ` +
            `${nAlgs} algs F2L-safe, ${nScrambles} scrambles produce their case`,
        );
      }
    } else {
      // 4×4: expand `[*]` with the set's parity alg, then parse/legality-check
      // everything on the 4x4 kpuzzle. TODO(M3): full 4x4 case-class checks.
      // Every 4×4 entry in SETS pins a parity alg; assert it rather than
      // expanding `[*]` to nothing if one is ever added without.
      if (!set.parity) throw new Error(`${set.name}: 4x4 set has no pinned parity alg`);
      const parity = set.parity;
      if (bindings.specialAlg !== set.parity) {
        fail(
          `specialAlg ${JSON.stringify(bindings.specialAlg)} does not match the pinned ` +
            `parity alg ${JSON.stringify(set.parity)}`,
        );
      }
      for (const c of cases) {
        if (c.algs.length === 0) {
          fail(`${c.name}: no algorithm strings`);
          continue;
        }
        c.algs = c.algs.map((/** @type {string} */ a) =>
          translate4x4Slices(expandParity(a, parity)),
        );
        for (const a of c.algs) {
          nAlgs++;
          const err = illegalReason(kpuzzle4, a);
          if (err) fail(`${c.name}: alg ${err}: ${a}`);
        }
        for (const s of c.scrambles) {
          nScrambles++;
          const err = illegalReason(kpuzzle4, s);
          if (err) fail(`${c.name}: scramble ${err}: ${s}`);
        }
      }
      if (setFailures === 0) {
        report.push(
          `✓ ${set.name}: ${cases.length} cases, ${nAlgs} algs parity-expanded & 4x4-legal, ` +
            `${nScrambles} scrambles 4x4-legal (case classes: TODO M3)`,
        );
      }
    }

    out[set.name] = cases;
  }

  if (setFailures > 0) report.push(`✗ ${set.name}: ${setFailures} failure(s)`);
  failures += setFailures;
}

console.log(report.join("\n"));
const allPresent = SETS.every((s) => Array.isArray(out[s.name]) && out[s.name].length > 0);
if (failures > 0 || !allPresent) {
  console.error(
    `\nValidation failed (${failures} failures` +
      `${allPresent ? "" : ", missing/empty sets"}) — src/data/extracted/jperm-raw.json left untouched`,
  );
  process.exit(1);
}
await mkdir(new URL("../src/data/extracted", import.meta.url), { recursive: true });
await writeFile(
  new URL("../src/data/extracted/jperm-raw.json", import.meta.url),
  JSON.stringify(out, null, 1),
);
console.log(`\nWrote src/data/extracted/jperm-raw.json (0 failures)`);
