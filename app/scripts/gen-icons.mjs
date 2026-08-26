#!/usr/bin/env node
// Rasterize the PWA icon set from public/favicon.svg — the mark's single source
// of truth. Edit the favicon, re-run this, never hand-edit the PNGs.
//
//   node scripts/gen-icons.mjs
//
// Requires rsvg-convert (brew install librsvg).

import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const PUBLIC = join(ROOT, "public");
const PAPER = "#fcfbf8"; // --paper: icons are opaque so the dark mark always reads

// `scale` is the mark's share of the canvas. Maskable icons must sit inside
// Android's 80% safe zone, so they get a much smaller mark on more background.
const TARGETS = [
  { out: "icons/icon-192.png", size: 192, scale: 0.76 },
  { out: "icons/icon-512.png", size: 512, scale: 0.76 },
  { out: "icons/maskable-192.png", size: 192, scale: 0.56 },
  { out: "icons/maskable-512.png", size: 512, scale: 0.56 },
  { out: "apple-touch-icon.png", size: 180, scale: 0.76 },
];

const favicon = readFileSync(join(PUBLIC, "favicon.svg"), "utf8");
const inner = favicon.match(/<svg[^>]*>([\s\S]*)<\/svg>/)?.[1];
if (!inner) throw new Error("favicon.svg: could not find the <svg> body");

// The mark is authored on a 64×64 viewBox.
const VB = 64;

function wrap(scale) {
  const span = VB / scale; // canvas side, in the mark's own units
  const off = (span - VB) / 2;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${span} ${span}">
<rect width="${span}" height="${span}" fill="${PAPER}"/>
<g transform="translate(${off} ${off})">${inner}</g>
</svg>`;
}

mkdirSync(join(PUBLIC, "icons"), { recursive: true });
const tmp = join(PUBLIC, ".icon-src.svg");
try {
  for (const { out, size, scale } of TARGETS) {
    writeFileSync(tmp, wrap(scale));
    execFileSync("rsvg-convert", [
      "-w", String(size), "-h", String(size), tmp, "-o", join(PUBLIC, out),
    ]);
    console.log(`  ${out}  ${size}×${size}`);
  }
} finally {
  rmSync(tmp, { force: true });
}
console.log(`${TARGETS.length} icons written from favicon.svg`);
