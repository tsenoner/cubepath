/**
 * The course, in course order — the one definition of it.
 *
 * The ordering IS the attribution rule `teaches.ts` applies: "first lesson
 * listing a case wins" is only meaningful against one definition of first.
 * Four other places sorted the collection themselves (the course index,
 * `Lesson.astro`, `LessonMeta.astro`, and the spec that GATES the rule), so a
 * tie-break or a draft filter added to one of them would have reached none of
 * the others — and the gate would have been checking the rule against its own
 * private ordering.
 *
 * WHY ITS OWN MODULE, and not a second export from `teaches.ts`. Sorting
 * lessons needs the content collection and nothing else, while `teaches.ts`
 * pulls `lib/trainer` -> `data/algs` -> `fullsets.gen` (the whole 83 KB case
 * set) and `lib/db` (the IndexedDB wrapper) behind it. The three navigation
 * surfaces above want the order, not the case data, and `search.ts` /
 * `casesearch.ts` are already split for exactly this reason. One definition,
 * in the lightest module that can hold it.
 *
 * Build-time only: this reaches into the content collection, so it must not be
 * imported from a client `<script>`.
 */
import { getCollection } from "astro:content";

export async function lessonsInOrder() {
  return (await getCollection("lessons")).sort((a, b) => a.data.order - b.data.order);
}
