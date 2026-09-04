/**
 * Which lesson teaches a case — the inverse of the `algorithms` and
 * `practice.groups` arrays a lesson already declares in its frontmatter.
 *
 * WHY IT EXISTS. The course linked outward and nothing linked back: from
 * /reference, /case or /practice there was no route into the lesson that
 * teaches the thing you are looking at. A reader who met a case in the trainer
 * and wanted the explanation had the header and the browser's Back button.
 *
 * DERIVED, NEVER DECLARED. Both directions come from the same frontmatter, so
 * they cannot disagree: `algorithms` gives an exact case -> lesson edge (42 of
 * them, and Lesson.astro already fails the build on an id that is not a real
 * case), and `practice.groups` gives a coarser group -> lesson edge, which
 * covers the sets a lesson teaches wholesale without listing 57 ids. Exact
 * wins where both apply.
 *
 * Build-time only: this reaches into the content collection, so it must not be
 * imported from a client `<script>`.
 */
import { getCollection } from "astro:content";
import { caseById } from "../data/algs";

import type { CaseDef } from "../data/algs";
import { TRAINER_GROUPS } from "./trainer";

export interface TeachingLesson {
  /** Content-collection id, i.e. the slug in /learn/<slug>/. */
  id: string;
  title: string;
  href: string;
}

interface Maps {
  byCase: Map<string, TeachingLesson>;
  byGroup: Map<string, TeachingLesson>;
}

/**
 * The PROMISE, not the resolved value.
 *
 * Caching the result only helps a caller that arrives after the first build has
 * finished, and the busiest caller does the opposite: /reference asks for all
 * ten sections through one `Promise.all`, so ten calls start before any of them
 * has anything to cache — ten `getCollection` reads and ten map builds where
 * one was intended. A promise is cached the moment the first call starts.
 */
let cached: Promise<Maps> | null = null;

/**
 * Does `lessonPhase` beat `heldPhase` as the home of this case?
 *
 * Only when the case names this lesson's phase and NOT the incumbent's. Both
 * halves are load-bearing: dropping the second turns "first in phase wins" into
 * "LAST in phase wins", because `beginner.righty` is claimed by three phase-1
 * lessons and every one of them would match. That is not hypothetical — it
 * moved righty from white-corners, where it is taught, to orient-corners, where
 * it is reused, until the incumbent test was added.
 */
function phaseWins(caseId: string, lessonPhase: string, heldPhase: string): boolean {
  const casePhase = caseById.get(caseId)?.phase;
  return casePhase === lessonPhase && casePhase !== heldPhase;
}

function build(): Promise<Maps> {
  cached ??= (async () => {
    const lessons = (await getCollection("lessons")).sort((a, b) => a.data.order - b.data.order);
    const byCase = new Map<string, TeachingLesson>();
    const byGroup = new Map<string, TeachingLesson>();
    /** The phase of the lesson currently holding each case — the incumbent. */
    const heldPhase = new Map<string, string>();

    for (const lesson of lessons) {
      const entry: TeachingLesson = {
        id: lesson.id,
        title: lesson.data.title,
        href: `/learn/${lesson.id}/`,
      };
      // First lesson in course order wins: a case introduced in Phase 3 and
      // revisited in Full CFOP should send the reader to where it was taught,
      // not to where it was recapped.
      //
      // UNLESS the case names a phase and one of its lessons is IN that phase,
      // which beats course order. A case carries ONE algorithm, and the lesson
      // that teaches THAT algorithm is the one a reader clicking "Taught in"
      // needs. The Hook is the case this exists for: `eo.hook` holds the
      // one-pass wide-f `f R U R' U' f'` and a cue saying front-right, both
      // Phase 1.5's, while yellow-cross (Phase 1) claims it first and teaches
      // two passes of the narrow `F R U R' U' F'` held back-left. Course order
      // sent the reader to a lesson that never prints the algorithm on the row.
      //
      // Narrow by construction: it only bites when TWO lessons claim one case
      // AND the case's phase is one of theirs. Six of the seven multi-claimed
      // cases are unaffected (their phase matches the earliest lesson anyway),
      // and a single-claimed case cannot reach it at all — which is what keeps
      // the 15 `pll.*` cases, whose `phase` ("full-pll") is a different
      // vocabulary from any lesson's, on the course-order rule.
      for (const caseId of lesson.data.algorithms) {
        const held = heldPhase.get(caseId);
        if (held !== undefined && !phaseWins(caseId, lesson.data.phase, held)) continue;
        byCase.set(caseId, entry);
        heldPhase.set(caseId, lesson.data.phase);
      }
      for (const group of lesson.data.practice.groups) {
        if (!byGroup.has(group)) byGroup.set(group, entry);
      }
    }
    return { byCase, byGroup };
  })();
  return cached;
}

/**
 * The lesson that teaches this case, or undefined if the course never names it.
 *
 * The fallback edge is keyed on the TRAINER group, which is the namespace
 * `practice.groups` uses — not on `CaseDef.group`, which is a recognition
 * grouping ("oll-fish-shape", "f2l-connected-pairs") in a different namespace
 * entirely. Passing the latter looked right and silently matched almost
 * nothing: 92 of the then-125 case pages had no "Taught in" link, because the
 * whole of Full OLL, F2L and Full PLL fell through. The trainer's own `member`
 * predicate is the mapping, so this is derived rather than a second table.
 */
export async function teachingLesson(def: CaseDef): Promise<TeachingLesson | undefined> {
  const { byCase, byGroup } = await build();
  const exact = byCase.get(def.id);
  if (exact) return exact;
  const group = TRAINER_GROUPS.find((g) => g.member(def));
  return group ? byGroup.get(group.key) : undefined;
}

/**
 * The lesson that teaches a whole set. `group` is a trainer group key, which is
 * also a /reference section id — the two lists are the same eleven strings.
 */
export async function lessonForGroup(group: string): Promise<TeachingLesson | undefined> {
  const { byGroup } = await build();
  return byGroup.get(group);
}
