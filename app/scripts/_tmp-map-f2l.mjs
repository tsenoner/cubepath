/**
 * TEMP one-time mapper (not committed): bucket JPerm Best-F2L Section 1 algs
 * by mechanically computed case class, map buckets to SCDB F2L 1..41 numbering
 * via SCDB setup algs, and emit src/data/extracted/f2l-raw.json.
 */
import { readFile, writeFile } from "node:fs/promises";
import { Alg } from "cubing/alg";
import { cube3x3x3 } from "cubing/puzzles";

const kpuzzle = await cube3x3x3.kpuzzle();
const solved = kpuzzle.defaultPattern();

// --- rotation normalization (as in extract-algs.mjs) ---
const ROTATIONS = [];
for (const a of ["", "x", "x2", "x'", "z", "z'"]) {
  for (const b of ["", "y", "y2", "y'"]) ROTATIONS.push([a, b].filter(Boolean).join(" "));
}
const IDENTITY_T = kpuzzle.identityTransformation();
const toT = (s) => (s ? kpuzzle.algToTransformation(new Alg(s)) : IDENTITY_T);
const ROTATION_T = ROTATIONS.map(toT);
const AUFS = ["", "U", "U2", "U'"];
const AUF_T = AUFS.map(toT);

function centersSolved(pattern) {
  const c = pattern.patternData.CENTERS;
  const s = solved.patternData.CENTERS;
  return c.pieces.every((p, i) => p === s.pieces[i]);
}
function leftRotNormalize(t) {
  for (const r of ROTATION_T) {
    const cand = r.applyTransformation(t);
    if (centersSolved(solved.applyTransformation(cand))) return cand;
  }
  throw new Error("leftRotNormalize: no rotation brings centers home");
}

// --- U-layer and FR-slot detection ---
const uTurn = solved.applyAlg(new Alg("U")).patternData;
const rTurn = solved.applyAlg(new Alg("R")).patternData;
const fTurn = solved.applyAlg(new Alg("F")).patternData;
const moved = (turn, orbit, i) => {
  const s = solved.patternData[orbit];
  return turn[orbit].pieces[i] !== s.pieces[i] || turn[orbit].orientation[i] !== s.orientation[i];
};
const U_SLOTS = {};
const FR_SLOTS = {};
for (const orbit of Object.keys(solved.patternData)) {
  const n = solved.patternData[orbit].pieces.length;
  U_SLOTS[orbit] = Array.from({ length: n }, (_, i) => moved(uTurn, orbit, i));
  FR_SLOTS[orbit] = Array.from(
    { length: n },
    (_, i) => moved(rTurn, orbit, i) && !moved(uTurn, orbit, i) && moved(fTurn, orbit, i),
  );
}
// FR piece ids (piece occupying the FR slot in the solved state)
const FR_PIECE = {};
for (const orbit of Object.keys(FR_SLOTS)) {
  const idxs = FR_SLOTS[orbit].map((v, i) => (v ? i : -1)).filter((i) => i >= 0);
  if (idxs.length > 1) throw new Error(`FR detection: ${orbit} has ${idxs.length} slots`);
  if (idxs.length === 1) FR_PIECE[orbit] = { slot: idxs[0], piece: solved.patternData[orbit].pieces[idxs[0]] };
}
console.log("FR slots:", JSON.stringify(FR_PIECE));

/** Non-(U-layer ∪ FR-slot) pieces all solved? */
function outsideF2LPairSolved(pattern) {
  const d = pattern.patternData;
  for (const orbit of Object.keys(d)) {
    const s = solved.patternData[orbit];
    for (let i = 0; i < s.pieces.length; i++) {
      if (U_SLOTS[orbit][i] || FR_SLOTS[orbit][i]) continue;
      if (d[orbit].pieces[i] !== s.pieces[i] || d[orbit].orientation[i] !== s.orientation[i])
        return false;
    }
  }
  return true;
}

/** Signature: where the FR corner+edge pieces sit (and their twist/flip). */
function frSignature(pattern) {
  const sig = [];
  for (const orbit of Object.keys(FR_PIECE)) {
    const { piece } = FR_PIECE[orbit];
    const d = pattern.patternData[orbit];
    const i = d.pieces.indexOf(piece);
    sig.push([orbit, i, d.orientation[i]]);
  }
  return JSON.stringify(sig);
}

/** Case class of a (rot-normalized) state transformation: min FR-signature over pre-AUF. */
function classOfState(t) {
  const keys = AUF_T.map((u) => frSignature(solved.applyTransformation(t.applyTransformation(u))));
  keys.sort();
  return keys[0];
}

const SOLVED_CLASS = classOfState(IDENTITY_T);

// --- SCDB reference: number -> {subgroup, setup} ---
const scdb = JSON.parse(await readFile("/tmp/scdb-f2l.json", "utf8"));
const classToNumber = new Map();
const numberInfo = new Map();
for (const [numStr, { subgroup, setup }] of Object.entries(scdb)) {
  const num = Number(numStr);
  const t = leftRotNormalize(toT(setup));
  const p = solved.applyTransformation(t);
  if (!outsideF2LPairSolved(p)) throw new Error(`SCDB setup for ${num} breaks non-FR F2L: ${setup}`);
  const cls = classOfState(t);
  if (cls === SOLVED_CLASS) throw new Error(`SCDB setup for ${num} is the solved class`);
  if (classToNumber.has(cls))
    throw new Error(`SCDB setups collide: ${num} vs ${classToNumber.get(cls)}`);
  classToNumber.set(cls, num);
  numberInfo.set(num, { subgroup, setup });
}
console.log(`SCDB: ${classToNumber.size} distinct case classes (expect 41)`);

// --- JPerm Section 1 algs ---
const jperm = JSON.parse(await readFile("/tmp/jperm-f2l-sec1.json", "utf8"));
const buckets = new Map(); // number -> algs[]
const problems = [];
for (const a of jperm) {
  let t;
  try {
    t = toT(a);
  } catch (e) {
    problems.push(`unparseable/illegal: ${a} (${e.message})`);
    continue;
  }
  let fwd, inv;
  try {
    fwd = leftRotNormalize(t);
    inv = leftRotNormalize(t.invert());
  } catch (e) {
    problems.push(`rotation-unnormalizable: ${a} (${e.message})`);
    continue;
  }
  if (!outsideF2LPairSolved(solved.applyTransformation(fwd))) {
    problems.push(`breaks pieces outside U+FR (forward): ${a}`);
    continue;
  }
  if (!outsideF2LPairSolved(solved.applyTransformation(inv))) {
    problems.push(`breaks pieces outside U+FR (pre-state): ${a}`);
    continue;
  }
  const cls = classOfState(inv);
  if (cls === SOLVED_CLASS) {
    problems.push(`identity-class alg: ${a}`);
    continue;
  }
  const num = classToNumber.get(cls);
  if (num === undefined) {
    problems.push(`class not in SCDB 41: ${a} -> ${cls}`);
    continue;
  }
  if (!buckets.has(num)) buckets.set(num, []);
  buckets.get(num).push(a);
}

console.log(`\nJPerm: ${jperm.length} algs, ${problems.length} problems, ${buckets.size} cases covered`);
for (const p of problems) console.log("  !", p);

const missing = [...numberInfo.keys()].filter((n) => !buckets.has(n));
console.log("cases lacking a JPerm FR-slot alg:", missing.join(", ") || "none");

// Fill gaps from SCDB's own Front-Right alternatives (vote order), keeping only
// algs that pass every invariant AND land in the case's own class.
const scdbFr = JSON.parse(await readFile("/tmp/scdb-fr-algs.json", "utf8"));
const numberToClass = new Map([...classToNumber].map(([c, n]) => [n, c]));
const filled = new Map();
for (const num of missing) {
  const verified = [];
  for (const a of scdbFr[num] ?? []) {
    let inv, fwd;
    try {
      const t = toT(a);
      fwd = leftRotNormalize(t);
      inv = leftRotNormalize(t.invert());
    } catch {
      continue;
    }
    if (!outsideF2LPairSolved(solved.applyTransformation(fwd))) continue;
    if (!outsideF2LPairSolved(solved.applyTransformation(inv))) continue;
    if (classOfState(inv) !== numberToClass.get(num)) {
      console.log(`  ! SCDB FR alg for ${num} lands in wrong class: ${a}`);
      continue;
    }
    verified.push(a);
    if (verified.length >= 3) break;
  }
  if (verified.length === 0) {
    console.log(`  !! case ${num}: NO verifiable alg from any source`);
    continue;
  }
  filled.set(num, verified);
}

const cases = [...numberInfo.keys()]
  .sort((a, b) => a - b)
  .map((num) => ({
    number: num,
    name: `F2L ${num}`,
    group: numberInfo.get(num).subgroup,
    setup: numberInfo.get(num).setup,
    source: buckets.has(num) ? "jperm-bestf2l" : "speedcubedb",
    algs: buckets.get(num) ?? filled.get(num) ?? [],
  }));
for (const c of cases)
  console.log(
    `${String(c.number).padStart(2)} [${c.group}] (${c.source}) ${c.algs.length} algs: ${c.algs.join(" | ")}`,
  );

const out = {
  meta: {
    description:
      "Standard 41 F2L cases (FR slot), numbered per SpeedCubeDB. Algs from " +
      "JPerm's Best F2L PDF Section 1 (FR-slot column); cases whose FR alg the PDF " +
      "presents only as a left-slot mirror are filled from SpeedCubeDB's Front Right " +
      "alternatives. setup = SpeedCubeDB case setup (applies the case to a solved cube). " +
      "Every alg + setup is mechanically verified: node scripts/verify-f2l.mjs",
    numbering: "https://speedcubedb.com/a/3x3/F2L",
    sources: {
      "jperm-bestf2l": "JPerm Best F2L PDF (bit.ly/bestf2l, updated 2021-08-08), Section 1",
      speedcubedb: "https://speedcubedb.com/a/3x3/F2L Front Right alternatives",
    },
  },
  f2l: cases,
};
await writeFile("/tmp/f2l-mapped.json", JSON.stringify(out, null, 1));
console.log("\nWrote /tmp/f2l-mapped.json");
