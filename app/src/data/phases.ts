/** Course phases in ladder order — the single registry for names and blurbs. */
export interface PhaseInfo {
  key: string;
  name: string;
  /**
   * Short form, for the course index's jump bar — mirroring `Section.nav` on
   * /reference, and for the same reason: eight full names ("Phase 1.5 — Speed
   * Tricks") make a chip strip three rows deep on a phone, which pushes the
   * first phase card off the screen the bar exists to save you scrolling to.
   */
  nav: string;
  blurb: string;
}

export const PHASES: PhaseInfo[] = [
  { key: "basics", name: "Basics", nav: "Basics", blurb: "Know the cube, read the moves." },
  {
    key: "phase-1",
    name: "Phase 1 — Beginner",
    nav: "Beginner",
    blurb: "Solve the cube reliably with one trigger.",
  },
  {
    key: "phase-1.5",
    name: "Phase 1.5 — Speed Tricks",
    nav: "Speed tricks",
    blurb: "Same method, fewer moves.",
  },
  {
    key: "phase-2",
    name: "Phase 2 — CFOP Switch",
    nav: "CFOP switch",
    blurb: "The last-layer order that never changes again.",
  },
  {
    key: "phase-3",
    name: "Phase 3 — Full 2-Look",
    nav: "Full 2-look",
    blurb: "Every case, one look, one algorithm.",
  },
  {
    key: "full-cfop",
    name: "Full CFOP",
    nav: "Full CFOP",
    blurb: "F2L pairs, all 21 PLL, all 57 OLL — the speed ceiling comes off.",
  },
  { key: "444", name: "4×4", nav: "4×4", blurb: "Your 3×3 + two new skills + parity." },
  { key: "555", name: "5×5", nav: "5×5", blurb: "4×4 skills — but centers are fixed again." },
];

export function phaseName(key: string): string {
  return PHASES.find((p) => p.key === key)?.name ?? key;
}

/**
 * The DOM id of a phase's card on the course index, and the fragment that
 * addresses it from anywhere else on the site.
 *
 * The prefix and the de-dotting are both load-bearing rather than decorative.
 * `444` and `phase-1.5` are perfectly legal ids and perfectly legal URL
 * fragments, but `#444` and `#phase-1.5` are not legal `querySelector`
 * arguments — the first starts with a digit, the second reads as a class
 * selector — so anything that later wants to find the element it scrolled to
 * would have to escape them. Deriving the id here means the index that writes
 * it and the breadcrumb that links to it cannot disagree.
 */
export function phaseAnchor(key: string): string {
  return `p-${key.replace(/\./g, "-")}`;
}
