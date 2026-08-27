/** Course phases in ladder order — the single registry for names and blurbs. */
export interface PhaseInfo {
  key: string;
  name: string;
  blurb: string;
}

export const PHASES: PhaseInfo[] = [
  { key: "basics", name: "Basics", blurb: "Know the cube, read the moves." },
  {
    key: "phase-1",
    name: "Phase 1 — Beginner",
    blurb: "Solve the cube reliably with one trigger.",
  },
  { key: "phase-1.5", name: "Phase 1.5 — Speed Tricks", blurb: "Same method, fewer moves." },
  {
    key: "phase-2",
    name: "Phase 2 — CFOP Switch",
    blurb: "The last-layer order that never changes again.",
  },
  {
    key: "phase-3",
    name: "Phase 3 — Full 2-Look",
    blurb: "Every case, one look, one algorithm.",
  },
  {
    key: "full-cfop",
    name: "Full CFOP",
    blurb: "F2L pairs, all 21 PLL, all 57 OLL — the speed ceiling comes off.",
  },
  { key: "444", name: "4×4", blurb: "Your 3×3 + two new skills + parity." },
  { key: "555", name: "5×5", blurb: "4×4 skills — but centers are fixed again." },
];

export function phaseName(key: string): string {
  return PHASES.find((p) => p.key === key)?.name ?? key;
}
