/**
 * Mechanical verification of src/data/extracted/f2l-raw.json — the 41 standard
 * F2L cases (FR slot, SpeedCubeDB numbering). Offline and self-contained: the
 * numbering ground truth is the embedded SCDB_SETUPS table (setup algs are
 * uncopyrightable facts, transcribed from speedcubedb.com/a/3x3/F2L).
 *
 * Checks (modeled on scripts/extract-algs.mjs):
 *  1. every alg parses (`new Alg`) and is legal on the 3x3 kpuzzle
 *  2. F2L invariant: applied to solved (rotation-normalized), an alg touches
 *     only the U layer and the FR pair — every piece outside U ∪ FR-slot stays
 *     solved. The FR slot is detected, not hardcoded: the piece slots that move
 *     under R and F but not U.
 *  3. solving check: pre-state = alg⁻¹ (left-rotation-normalized — an alg with
 *     net rotation carries it on the LEFT of the inverse) applied to solved;
 *     the pre-state is FR-local, and applying the alg to it leaves every
 *     non-U-layer piece solved (F2L complete; last layer arbitrary)
 *  4. case identity + distinctness: each case's class — the (position,
 *     orientation) of the FR corner + FR edge pieces in the pre-state, up to
 *     pre-AUF — must equal the class pinned by its number's SCDB setup; the 41
 *     setup classes are pairwise distinct and none is the solved class
 *  5. totals: exactly 41 cases numbered 1..41, each with ≥1 alg (the primary,
 *     algs[0], is therefore verified), name/group present, setup matches the
 *     pinned table
 *
 * Usage: node scripts/verify-f2l.mjs   (exits nonzero on any failure)
 */
import { readFile } from "node:fs/promises";
import { Alg } from "cubing/alg";
import { cube3x3x3 } from "cubing/puzzles";

import { makeKit } from "./lib/kpuzzle-utils.mjs";

// Numbering ground truth: SpeedCubeDB case setups (setup applied to a solved
// cube produces the case at the FR slot). https://speedcubedb.com/a/3x3/F2L
const SCDB_SETUPS = {
  1: "F R' F' R",
  2: "R' F R F'",
  3: "F' U F",
  4: "R U' R'",
  5: "R U R' U2' R U' R' U",
  6: "F' U' F U2' F' U F U'",
  7: "R U R' U2' R U2' R' U",
  8: "r' U' R2 U' R2' U2' r",
  9: "F' U F U' R U R' U",
  10: "R U' R' U' R U' R' U",
  11: "F' U F U' R U2' R' U",
  12: "R U R' U2' R U R' U' R U R'",
  13: "r U2' R' U R U' R' U M",
  14: "R U' R' U' R U R' U",
  15: "R U R' U' R U R' U2' R U' R'",
  16: "F' U F U2' R U R'",
  17: "R U' R' U R U2' R'",
  18: "R U R' U' R U R' F R' F' R",
  19: "R U R' U' R U2' R' U'",
  20: "R U R' F R' F' R2' U R' U",
  21: "R U' R' U2' R U R'",
  22: "F' L' U2' L F",
  23: "R U' R' U R U' R' U2' R U' R'",
  24: "R U R' F R U R' U' F'",
  25: "F' R U R' U' R' F R",
  26: "F' U' F U R U R' U'",
  27: "R U R' U' R U R'",
  28: "R' F R F' U R U' R'",
  29: "F R' F' R F R' F' R",
  30: "R U' R' U R U' R'",
  31: "R U R' F R' F' R U",
  32: "R U' R' U R U' R' U R U' R'",
  33: "R U R' U2' R U R' U",
  34: "R U' R' U2' R U' R' U'",
  35: "F' U F U' R U' R' U",
  36: "R U' R' U2' F R' F' R U2'",
  37: "R U' R U2' F R2' F' U2' R2'",
  38: "R U' R' U R U2' R' U R U' R'",
  39: "R U' R' U' R U R' U2' R U' R'",
  40: "R U R' F U R U' R' F' R U R'",
  41: "R F U R U' R' F' U' R'",
};

const kpuzzle = await cube3x3x3.kpuzzle();

// Shared rotation/normalization kit. Left- vs right-rotation-normalize
// matters: forward patterns rotate back AFTER (right-compose), inverted
// transformations (pre-states, alg⁻¹) carry any net rotation on the LEFT —
// using the wrong side conjugates the state onto the wrong slot for algs
// with net rotation (leading y etc.).
const { solved, ID: IDENTITY_T, toT, AUF_T, rightRotNormalize, leftRotNormalize } = makeKit(kpuzzle);

// U-layer and FR-slot piece slots (detected, not hardcoded): FR slot = moves
// under R and F but not U (corners: DFR; edges: FR).
const uTurn = solved.applyAlg(new Alg("U")).patternData;
const rTurn = solved.applyAlg(new Alg("R")).patternData;
const fTurn = solved.applyAlg(new Alg("F")).patternData;
const movedBy = (turn, orbit, i) => {
  const s = solved.patternData[orbit];
  return turn[orbit].pieces[i] !== s.pieces[i] || turn[orbit].orientation[i] !== s.orientation[i];
};
const U_SLOTS = {};
const FR_SLOTS = {};
const FR_PIECE = {}; // orbit -> piece id of the FR-pair piece
for (const orbit of Object.keys(solved.patternData)) {
  const n = solved.patternData[orbit].pieces.length;
  U_SLOTS[orbit] = Array.from({ length: n }, (_, i) => movedBy(uTurn, orbit, i));
  FR_SLOTS[orbit] = Array.from(
    { length: n },
    (_, i) => movedBy(rTurn, orbit, i) && !movedBy(uTurn, orbit, i) && movedBy(fTurn, orbit, i),
  );
  const idxs = FR_SLOTS[orbit].flatMap((v, i) => (v ? [i] : []));
  if (idxs.length > 1) throw new Error(`FR-slot detection: ${orbit} matched ${idxs.length} slots`);
  if (idxs.length === 1) FR_PIECE[orbit] = solved.patternData[orbit].pieces[idxs[0]];
}
if (!("CORNERS" in FR_PIECE) || !("EDGES" in FR_PIECE)) {
  throw new Error("FR-slot detection failed to find the corner+edge slots");
}

/** Every piece outside the U layer solved? (setUnion=false) — or outside U ∪ FR slot (true). */
function outsideSolved(pattern, { allowFRSlot }) {
  const d = pattern.patternData;
  for (const orbit of Object.keys(d)) {
    const s = solved.patternData[orbit];
    for (let i = 0; i < s.pieces.length; i++) {
      if (U_SLOTS[orbit][i] || (allowFRSlot && FR_SLOTS[orbit][i])) continue;
      if (d[orbit].pieces[i] !== s.pieces[i] || d[orbit].orientation[i] !== s.orientation[i]) {
        return false;
      }
    }
  }
  return true;
}

/** Where the FR corner + FR edge pieces sit, and their twist/flip. */
function frSignature(pattern) {
  const sig = [];
  for (const orbit of Object.keys(FR_PIECE)) {
    const d = pattern.patternData[orbit];
    const i = d.pieces.indexOf(FR_PIECE[orbit]);
    sig.push([orbit, i, d.orientation[i]]);
  }
  return JSON.stringify(sig);
}

/** Case class of a rot-normalized pre-state: min FR signature over pre-AUF U turns. */
function classOfState(t) {
  const keys = AUF_T.map((u) => frSignature(solved.applyTransformation(t.applyTransformation(u))));
  keys.sort();
  return keys[0];
}
const SOLVED_CLASS = classOfState(IDENTITY_T);

const report = [];
let failures = 0;
const fail = (msg) => {
  report.push(`✗ ${msg}`);
  failures++;
};

// --- pin the 41 case classes from the SCDB setups ---
const numberToClass = new Map();
const classToNumber = new Map();
for (const [numStr, setup] of Object.entries(SCDB_SETUPS)) {
  const num = Number(numStr);
  let t;
  try {
    t = leftRotNormalize(toT(setup));
  } catch (e) {
    fail(`case ${num}: pinned setup unusable (${e.message}): ${setup}`);
    continue;
  }
  if (!outsideSolved(solved.applyTransformation(t), { allowFRSlot: true })) {
    fail(`case ${num}: pinned setup is not FR-local: ${setup}`);
    continue;
  }
  const cls = classOfState(t);
  if (cls === SOLVED_CLASS) fail(`case ${num}: pinned setup is the solved class: ${setup}`);
  else if (classToNumber.has(cls)) {
    fail(`case ${num}: pinned setup collides with case ${classToNumber.get(cls)}`);
  } else {
    classToNumber.set(cls, num);
    numberToClass.set(num, cls);
  }
}
if (numberToClass.size === 41) {
  report.push("✓ pinned setups: 41 pairwise-distinct case classes, all FR-local, none solved");
}

// --- verify the dataset ---
const dataUrl = new URL("../src/data/extracted/f2l-raw.json", import.meta.url);
const data = JSON.parse(await readFile(dataUrl, "utf8"));
const cases = data.f2l;
if (!Array.isArray(cases)) {
  fail("f2l-raw.json has no `f2l` case array");
  finish();
}

const seen = new Set();
let nAlgs = 0;
for (const c of cases) {
  const label = `case ${c.number}`;
  if (!Number.isInteger(c.number) || c.number < 1 || c.number > 41) {
    fail(`${label}: number out of range 1..41`);
    continue;
  }
  if (seen.has(c.number)) fail(`${label}: duplicate number`);
  seen.add(c.number);
  if (c.name !== `F2L ${c.number}`) fail(`${label}: name mismatch: ${c.name}`);
  if (typeof c.group !== "string" || !c.group) fail(`${label}: missing group`);
  if (c.setup !== SCDB_SETUPS[c.number]) fail(`${label}: setup differs from pinned table`);
  if (!Array.isArray(c.algs) || c.algs.length === 0) {
    fail(`${label}: no algorithms`);
    continue;
  }
  const wantClass = numberToClass.get(c.number);
  for (const a of c.algs) {
    nAlgs++;
    // 1. parse + legality
    let t;
    try {
      t = toT(a);
    } catch (e) {
      fail(`${label}: alg does not parse or is illegal (${e.message}): ${a}`);
      continue;
    }
    // 2. F2L invariant (forward)
    let fwd, inv;
    try {
      fwd = rightRotNormalize(t);
      inv = leftRotNormalize(t.invert());
    } catch (e) {
      fail(`${label}: centers not restorable by a rotation (${e.message}): ${a}`);
      continue;
    }
    if (!outsideSolved(solved.applyTransformation(fwd), { allowFRSlot: true })) {
      fail(`${label}: alg touches pieces outside U layer + FR pair: ${a}`);
      continue;
    }
    // 3. solving check from the pre-state
    if (!outsideSolved(solved.applyTransformation(inv), { allowFRSlot: true })) {
      fail(`${label}: pre-state not FR-local: ${a}`);
      continue;
    }
    const after = rightRotNormalize(inv.applyTransformation(t));
    if (!outsideSolved(solved.applyTransformation(after), { allowFRSlot: false })) {
      fail(`${label}: pre-state + alg does not complete F2L: ${a}`);
      continue;
    }
    // 4. case identity (⇒ distinctness across cases, up to pre-AUF)
    const cls = classOfState(inv);
    if (cls !== wantClass) {
      const got = classToNumber.get(cls);
      fail(`${label}: alg solves ${got ? `case ${got}` : "an unknown class"}, not this case: ${a}`);
    }
  }
}
// 5. totals
if (cases && cases.length !== 41) fail(`expected 41 cases, got ${cases.length}`);
for (let n = 1; n <= 41; n++) if (!seen.has(n)) fail(`case ${n} missing`);
if (failures === 0) {
  report.push(
    `✓ ${cases.length} cases numbered 1..41, ${nAlgs} algs: all parse, preserve F2L outside ` +
      "the FR pair, complete F2L from their pre-state, and match their number's case class",
  );
}
finish();

function finish() {
  console.log(report.join("\n"));
  if (failures > 0) {
    console.error(`\nF2L verification FAILED (${failures} failure(s))`);
    process.exit(1);
  }
  console.log("\nF2L verification passed (0 failures)");
  process.exit(0);
}
