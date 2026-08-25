import { Alg } from "cubing/alg";
import { puzzles } from "cubing/puzzles";
const kp = await puzzles["5x5x5"].kpuzzle();
const solved = kp.defaultPattern();
const T = (s) => kp.algToTransformation(new Alg(s));
const same = (a, b) => T(a).isIdentical(T(b));

// slice semantics
for (const [a, b] of [
  ["M", "3L"], ["M", "3R'"], ["E", "3D"], ["E", "3U'"], ["S", "3F"],
  ["r' l", "x' M'"], ["r l'", "M x"], ["m", "2-4Lw"], ["m", "2-4Rw'"],
]) {
  console.log(JSON.stringify(a), "==", JSON.stringify(b), ":", same(a, b));
}

// Edge-position groups: for each EDGES/EDGES2 slot, which outer face turns move it
const FACES = ["U", "D", "L", "R", "F", "B"];
const faceT = Object.fromEntries(FACES.map((f) => [f, T(f).invert()]));
// slot i is moved by face f if applying f to solved changes slot i
const groups = {};
for (const orbit of ["EDGES", "EDGES2"]) {
  const s = solved.patternData[orbit];
  for (let i = 0; i < s.pieces.length; i++) {
    const touched = [];
    for (const f of FACES) {
      const p = solved.applyTransformation(kp.algToTransformation(new Alg(f)));
      const d = p.patternData[orbit];
      if (d.pieces[i] !== s.pieces[i] || d.orientation[i] !== s.orientation[i]) touched.push(f);
    }
    const key = touched.sort().join("");
    (groups[key] ??= []).push(`${orbit}:${i}`);
  }
}
console.log("\nedge groups:");
for (const [k, v] of Object.entries(groups)) console.log(" ", k, "->", v.join(" "));
