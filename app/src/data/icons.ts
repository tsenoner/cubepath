/** Case id → generated diagram path (synced by scripts/sync-diagrams.sh). */
const ICONS: Record<string, string> = {
  "eo.dot": "/diagrams/oll/oll_dot.svg",
  "eo.hook": "/diagrams/oll/oll_hook.svg",
  "eo.line": "/diagrams/oll/oll_line.svg",
  "oll.27": "/diagrams/oll/oll_sune.svg",
  "oll.26": "/diagrams/oll/oll_antisune.svg",
  "oll.22": "/diagrams/oll/oll_pi.svg",
  "oll.23": "/diagrams/oll/oll_headlights.svg",
  "oll.21": "/diagrams/oll/oll_double_headlights.svg",
  "oll.24": "/diagrams/oll/oll_chameleon.svg",
  "oll.25": "/diagrams/oll/oll_bowtie.svg",
  "pll.t": "/diagrams/pll/pll_tperm.svg",
  "pll.y": "/diagrams/pll/pll_yperm.svg",
  "pll.ua": "/diagrams/pll/pll_ua.svg",
  "pll.ub": "/diagrams/pll/pll_ub.svg",
  "pll.h": "/diagrams/pll/pll_hperm.svg",
  "pll.z": "/diagrams/pll/pll_zperm.svg",
};

function fullSetIcon(id: string): string | undefined {
  const oll = id.match(/^oll\.(\d+)$/);
  if (oll) return `/diagrams/oll-full/oll_${oll[1]!.padStart(2, "0")}.svg`;
  const pll = id.match(/^pll\.([a-z]+)$/);
  if (pll) return `/diagrams/pll-full/pll_full_${pll[1]}.svg`;
  return undefined;
}

export function caseIcon(id: string): string | undefined {
  // Curated 2-look icons keep the course's original diagrams; everything
  // else falls back to the generated full-set diagrams.
  return ICONS[id] ?? fullSetIcon(id);
}
