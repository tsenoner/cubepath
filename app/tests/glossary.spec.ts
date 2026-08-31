/**
 * The glossary, gated against the two ways a glossary goes wrong.
 *
 * IT DEFINES WORDS NOBODY USES. A glossary written from a mental list of
 * cubing jargon rather than from this project's own prose is a page of terms a
 * reader will never meet, and it hides the ones they will. Every term here has
 * to appear in a lesson, in the guide, or on a printed card.
 *
 * IT DISAGREES WITH THE CARDS. `tools/cubepath/src/cubepath/glossary.py` is the
 * printable card set's own vocabulary, with its own six-word glosses, and it is
 * enforced on every rendered card. Two vocabularies that drift apart is how a
 * reader ends up with a card and a page that define "parity" differently, so
 * the site's list must cover the card's.
 *
 * Plus the mechanical checks the rehype pass depends on: unique slugs, no
 * self-reference, and every `also` variant distinct — a variant claimed by two
 * entries would make which one wins depend on iteration order.
 */
import { readFileSync, readdirSync } from "node:fs";

import { describe, expect, test } from "vitest";

import { GLOSSARY, GLOSS_ENTRIES, glossByTerm, glossSlug } from "../src/data/glossary";

const LESSON_DIR = new URL("../src/content/lessons/", import.meta.url);
const LESSONS = readdirSync(LESSON_DIR)
  .filter((f) => f.endsWith(".mdx"))
  .map((f) => readFileSync(new URL(f, LESSON_DIR), "utf8"));
/** The two prose surfaces a reader meets: the 25 lessons and the PDF guide. */
const ALL_PROSE = [
  ...LESSONS,
  readFileSync(new URL("../../guide/cubepath.md", import.meta.url), "utf8"),
]
  .join("\n")
  .toLowerCase();

/** The card set's vocabulary, read out of the Python source rather than retyped. */
function cardGlossTerms(): string[] {
  const py = readFileSync(
    new URL("../../tools/cubepath/src/cubepath/glossary.py", import.meta.url),
    "utf8",
  );
  const block = /GLOSS: dict\[str, str\] = \{(.*?)^\}/ms.exec(py);
  expect(block, "glossary.py no longer declares GLOSS as a plain dict literal").toBeTruthy();
  return [...block![1]!.matchAll(/^\s*"([^"]+)":/gm)].map((m) => m[1]!);
}

describe("glossary", () => {
  test("every term is a word this project actually uses", () => {
    // Three surfaces count, and the third is the reason this is not simply
    // "appears in a lesson": the printable cards carry vocabulary the lessons
    // do not ("sledgehammer", "AUF", "adjacent corner swap"), and a card is a
    // piece of paper with no glossary on the back. A reader who meets a word
    // there has to be able to look it up here.
    const onCards = new Set(cardGlossTerms().map((t) => t.toLowerCase()));
    const unused = GLOSS_ENTRIES.filter((e) => {
      const forms = [e.term, ...(e.also ?? [])].map((s) => s.toLowerCase());
      return !forms.some((f) => ALL_PROSE.includes(f) || onCards.has(f));
    }).map((e) => e.term);
    expect(unused, "defined but used nowhere — lessons, guide or cards").toEqual([]);
  });

  test("every term the printable cards gloss is defined here too", () => {
    const known = new Set(
      GLOSS_ENTRIES.flatMap((e) => [e.term, ...(e.also ?? [])]).map((s) => s.toLowerCase()),
    );
    const missing = cardGlossTerms().filter((t) => !known.has(t.toLowerCase()));
    expect(missing, "the cards define these and the site does not").toEqual([]);
  });

  test("slugs are unique — they are the anchors a few hundred lesson links point at", () => {
    const slugs = GLOSS_ENTRIES.map((e) => glossSlug(e.term));
    expect(new Set(slugs).size).toBe(slugs.length);
    for (const slug of slugs) expect(slug).toMatch(/^[a-z0-9-]+$/);
  });

  test("no variant is claimed by two entries", () => {
    const seen = new Map<string, string>();
    for (const entry of GLOSS_ENTRIES) {
      for (const form of [entry.term, ...(entry.also ?? [])]) {
        const key = form.toLowerCase();
        expect(seen.has(key), `"${form}" is claimed by ${seen.get(key)} and ${entry.term}`).toBe(
          false,
        );
        seen.set(key, entry.term);
      }
    }
  });

  test("cross-references resolve, and nothing points at itself", () => {
    for (const entry of GLOSS_ENTRIES) {
      for (const term of entry.see ?? []) {
        expect(glossByTerm.has(term), `${entry.term} → ${term}`).toBe(true);
        expect(term, `${entry.term} references itself`).not.toBe(entry.term);
      }
    }
  });

  test("the short definition stays short enough to read in a hover card", () => {
    for (const entry of GLOSS_ENTRIES) {
      expect(entry.short.length, `${entry.term}: ${entry.short.length} chars`).toBeLessThanOrEqual(
        200,
      );
      expect(entry.short.trim().endsWith("."), `${entry.term}: no full stop`).toBe(true);
    }
  });

  test("every group has entries and every entry has a group", () => {
    expect(GLOSSARY.length).toBeGreaterThan(0);
    for (const group of GLOSSARY) expect(group.entries.length, group.title).toBeGreaterThan(0);
  });
});
