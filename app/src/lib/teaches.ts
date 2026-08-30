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
 * they cannot disagree: `algorithms` gives an exact case -> lesson edge (37 of
 * them, and Lesson.astro already fails the build on an id that is not a real
 * case), and `practice.groups` gives a coarser group -> lesson edge, which
 * covers the sets a lesson teaches wholesale without listing 57 ids. Exact
 * wins where both apply.
 *
 * Build-time only: this reaches into the content collection, so it must not be
 * imported from a client `<script>`.
 */
import { getCollection } from "astro:content";

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

let cached: Maps | null = null;

async function build(): Promise<Maps> {
  if (cached) return cached;
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
  cached = { byCase, byGroup };
  return cached;
}

/**
 * The lesson that teaches this case, or undefined if the course never names it.
 * `group` is the case's own group key, used as the fallback edge.
 */
export async function teachingLesson(
  caseId: string,
  group: string,
): Promise<TeachingLesson | undefined> {
  const { byCase, byGroup } = await build();
  return byCase.get(caseId) ?? byGroup.get(group);
}

/**
 * The lesson that teaches a whole set. `group` is a trainer group key, which is
 * also a /reference section id — the two lists are the same eleven strings.
 */
export async function lessonForGroup(group: string): Promise<TeachingLesson | undefined> {
  const { byGroup } = await build();
  return byGroup.get(group);
}
