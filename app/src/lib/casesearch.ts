/**
 * A case's recognition cue and its search haystack, in one place.
 *
 * BUILD-TIME ONLY. It reads `fullsets.rich.gen.ts`, which is the big half of
 * the dataset and must never reach the client — which is precisely why this
 * cannot live in `lib/search.ts`, whose `filter`/`normalize` ARE imported by
 * the /reference and /glossary client scripts.
 *
 * WHY IT EXISTS. Four surfaces needed "the cue for this case" and three needed
 * "everything this case can be found by", and each wrote the rule out again:
 * the lean generated entries omit `recognition`, so every reader has to fall
 * back to RICH, and every haystack has to name the same five sources in the
 * same order. `lib/search.ts` already stopped the two haystack BUILDERS from
 * drifting; this stops their ARGUMENTS from drifting, which is the half that
 * was still copied — CaseRow, /reference and the unit corpus each spelled the
 * fallback out, so a third source of cues would have had to be added in three
 * places or silently apply to some surfaces and not others.
 */
import type { CaseDef } from "../data/algs";
import { RICH } from "../data/fullsets.rich.gen";
import { haystackFor } from "./search";

/**
 * The cue a case is recognized by. Curated entries carry their own; the lean
 * generated ones leave it to RICH.
 */
export function recognitionOf(def: CaseDef): string | undefined {
  return def.recognition ?? RICH[def.id]?.recognition;
}

/**
 * Everything this case can be found by.
 *
 * `extra` is text the PAGE knows and the case does not — /reference passes the
 * section's own words, so a reader who types a heading they can see finds the
 * cases under it.
 */
export function caseHaystack(def: CaseDef, extra?: string): string {
  return haystackFor({
    name: def.name,
    recognition: recognitionOf(def),
    id: def.id,
    group: def.group,
    extra,
  });
}
