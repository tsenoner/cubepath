import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

/**
 * Lesson frontmatter.
 *
 * The four original fields (title/description/phase/order) could only produce a
 * title, a subtitle and a prev/next pair — so a 294-word concept page and a
 * 30-case reference page rendered identically, no lesson could state what it
 * assumed you already knew, and not one of the 25 handed the reader to the
 * trainer. The fields below exist so `Lesson.astro` can render those things
 * once, for every lesson, instead of 25 MDX bodies improvising them.
 *
 * Every field here is filled on all 25 lessons. Do not add one you cannot fill:
 * an optional metadata field is a field the layout has to render two ways.
 */
const lessons = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/lessons" }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    /** Course section, e.g. "basics", "phase-1", "phase-1.5", "phase-2", "phase-3". */
    phase: z.string(),
    /** Global ordering across the whole 3×3 course. */
    order: z.number(),

    /** Reading time plus the first attempt at the cube, in minutes. Rendered as "≈ N min". */
    minutes: z.number().int().positive(),

    /**
     * "What you'll learn" — 2 to 4 outcomes, each a thing the reader can do
     * afterwards, not a topic the lesson mentions.
     */
    objectives: z.array(z.string()).min(2).max(4),

    /**
     * Lesson ids (filenames without `.mdx`) that must come first. Validated
     * against the collection in Lesson.astro, so a typo fails `astro build`.
     */
    prerequisites: z.array(z.string()).default([]),

    /**
     * Case ids whose ALGORITHM this lesson teaches, e.g. "oll.27". Validated
     * against `caseById`. Empty for lessons that teach a technique rather than
     * a case set — which is itself the signal CLAUDE.md's "as few new
     * algorithms as possible per phase" rule needs to be checkable.
     *
     * This field decides ATTRIBUTION: `teaches.ts` sends a case's "Taught in"
     * link to the first lesson listing it, and `tests/teaches.spec.ts` holds
     * each case's phase to that lesson's. So it answers "who teaches this", and
     * only that. For a case a lesson merely SHOWS, use `shows` — the two were
     * one field, which is how trimming this array to fix an attribution bug
     * silently cut two links off the lesson's own case list.
     */
    algorithms: z.array(z.string()).default([]),

    /**
     * Case ids this lesson PICTURES but does not teach the algorithm for.
     *
     * Rendered in the lesson's case list beside `algorithms` and invisible to
     * attribution — nothing here can make a lesson the answer to "Taught in".
     * yellow-cross is the case it exists for: it walks the reader from Dot
     * through Hook to Line and draws all three, but the only algorithm it
     * prints is the Line's, and the other two are Phase 1.5's.
     */
    shows: z.array(z.string()).default([]),

    /**
     * The closing handoff. `Lesson.astro` renders it as the `Practice` section
     * so every lesson ends by pointing somewhere, and no lesson can forget to.
     *
     * `groups` are TRAINER_GROUPS keys (src/lib/trainer.ts) and become
     * `/practice/?group=<key>` deep links. `links` covers the lessons no
     * trainer set matches — notation, anatomy, the reduction steps — which
     * point at the most useful next action instead.
     */
    practice: z.object({
      groups: z.array(z.string()).default([]),
      links: z
        .array(
          z.object({
            href: z.string(),
            label: z.string(),
            /**
             * Does following this link mean "done with this lesson"?
             *
             * DECLARED, not inferred. `Lesson.astro` used to tag an exit when
             * its href started with `/practice/` or `/learn/`, which is a guess
             * about intent made from a URL shape: a lesson linking BACK to a
             * prerequisite, or sideways to a drill it recommends mid-lesson,
             * would have credited itself and hidden itself from Resume
             * permanently. The person writing the link is the one who knows.
             *
             * Defaults to FALSE because that is the safe direction — an
             * uncredited lesson is a lesson the reader is offered again, while
             * a wrongly credited one disappears from the course with no way
             * back. `white-cross.mdx` offers `/print`, which is the case the
             * whole rule exists for.
             */
            advance: z.boolean().default(false),
          }),
        )
        .default([]),
      /** One sentence: what to drill, and what "done enough" looks like. */
      note: z.string(),
    }),
  }),
});

export const collections = { lessons };
