import { caseById } from "./algs";

/**
 * Case id → diagram icon path. The path is data on the CaseDef itself:
 * curated entries carry their course diagrams, generated entries the
 * full-set diagrams emitted by scripts/gen-cases.mjs.
 */
export function caseIcon(id: string): string | undefined {
  return caseById.get(id)?.icon;
}
