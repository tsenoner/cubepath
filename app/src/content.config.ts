import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const lessons = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/lessons" }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    /** Course section, e.g. "basics", "phase-1", "phase-1.5", "phase-2", "phase-3". */
    phase: z.string(),
    /** Global ordering across the whole 3×3 course. */
    order: z.number(),
  }),
});

export const collections = { lessons };
