/**
 * The lesson directory as the filesystem sees it.
 *
 * Three specs read the raw `.mdx` files rather than the content collection —
 * `teaches.spec.ts` to prove the collection is not empty, `glossary.spec.ts` to
 * search the prose, `algs.spec.ts` to scrape player embeds — and each had its
 * own copy of this URL and this filter. Lessons moving, or gaining a second
 * extension, would then be three edits that fail three different ways.
 */
import { readFileSync, readdirSync } from "node:fs";

export const LESSON_DIR = new URL("../src/content/lessons/", import.meta.url);

/** The lesson filenames, sorted: `["align-edges.mdx", …]`. */
export function lessonFiles(): string[] {
  return readdirSync(LESSON_DIR)
    .filter((f) => f.endsWith(".mdx"))
    .sort();
}

/** Each lesson's source text, in the same order. */
export function lessonSources(): string[] {
  return lessonFiles().map((f) => readFileSync(new URL(f, LESSON_DIR), "utf8"));
}
