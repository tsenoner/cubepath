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
 * A lesson lists the cases whose ALGORITHM it teaches, not every pattern it
 * shows — `tests/teaches.spec.ts` holds each case's phase to its lesson's, so a
 * listing that breaks that fails the build rather than sending "Taught in" to
 * a lesson that never prints the row's algorithm (the Hook did exactly that;
 * docs/DECISIONS.md § "The Hook's two holds").
 *
 * Build-time only: this reaches into the content collection, so it must not be
 * imported from a client `<script>`.
 */
import { getCollection } from "astro:content";

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

function build(): Promise<Maps> {
  cached ??= (async () => {
    const lessons = (await getCollection("lessons")).sort((a, b) => a.data.order - b.data.order);
    const byCase = new Map<string, TeachingLesson>();
    const byGroup = new Map<string, TeachingLesson>();

    for (const lesson of lessons) {
      const entry: TeachingLesson = {
        id: lesson.id,
        title: lesson.data.title,
        href: `/learn/${lesson.id}/`,
      };
      // First lesson in course order wins: a case introduced in Phase 3 and
      // revisited in Full CFOP should send the reader to where it was taught,
      // not to where it was recapped.
      for (const caseId of lesson.data.algorithms) {
        if (!byCase.has(caseId)) byCase.set(caseId, entry);
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
