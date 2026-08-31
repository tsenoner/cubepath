/**
 * Link the FIRST mention of each glossary term in a lesson to its entry, and
 * hang the definition off it as a hover/focus card.
 *
 * WHY A PLUGIN AND NOT A COMPONENT. The alternative was a `<Term>` component
 * hand-placed in the MDX. That is 25 files to edit, a judgement call at every
 * occurrence, and — the reason it was rejected — a list that rots: a term
 * renamed in `src/data/glossary.ts` leaves dead markup in prose nobody
 * re-reads. Here the prose is untouched and the glossary is the only source.
 *
 * WHY IT LIVES IN scripts/. Everything here is type-checked (`checkJs`, see
 * scripts/tsconfig.json), and this file decides what appears inside 25 lessons.
 * It generates markup rather than data, which is the one way it differs from
 * its neighbours.
 *
 * WHAT IT PRODUCES is a plain anchor, with no JavaScript anywhere:
 *
 *   <a class="gloss" href="/glossary/#auf" data-gloss="Adjust the Upper …">AUF</a>
 *
 * The definition rides in `data-gloss` and `Lesson.astro`'s CSS shows it with
 * `content: attr(data-gloss)` on hover and on keyboard focus. An anchor is
 * focusable by construction, so the keyboard case needs no tabindex and no
 * script; and because it is a real link, a touch reader — who gets no hover —
 * taps through to the full entry instead of being handed nothing.
 *
 * WHAT IT WILL NOT TOUCH: headings (a link in a heading fights the anchor
 * link), existing links (nested anchors are invalid), code and algorithm
 * markup (`R U R'` must never acquire a tooltip), and the components that
 * render their own content from the dataset.
 */

import { GLOSS_ENTRIES, glossSlug } from "../src/data/glossary.ts";

/** Elements whose subtree is left alone. */
const SKIP_TAGS = new Set([
  "a",
  "code",
  "pre",
  "kbd",
  "samp",
  "abbr",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
]);

/**
 * MDX components that render from the dataset rather than from the prose
 * around them. Glossing their children would put a tooltip inside an algorithm
 * or a case row.
 */
const SKIP_COMPONENTS = new Set(["AlgText", "TwistyPlayer", "CaseRow", "LessonMeta"]);

/** Escape a term for use inside a RegExp. */
const escape = (/** @type {string} */ s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * One matcher for the whole glossary, longest phrase first so "edge pair"
 * wins over "edge" and "wide turn" over "turn". `\b` on both ends keeps
 * "corner" out of "corners" unless `also` asked for it, which is what makes
 * the inflections explicit data rather than a guess about English.
 */
const PATTERN = (() => {
  /** @type {{ text: string; entry: (typeof GLOSS_ENTRIES)[number] }[]} */
  const variants = [];
  for (const entry of GLOSS_ENTRIES) {
    for (const text of [entry.term, ...(entry.also ?? [])]) variants.push({ text, entry });
  }
  variants.sort((a, b) => b.text.length - a.text.length);
  const source = variants.map((v) => escape(v.text)).join("|");
  return {
    /** Rebuilt per document: a shared /g regex carries lastIndex between files. */
    make: () => new RegExp(`\\b(?:${source})\\b`, "gi"),
    /** matched text (lowercased) -> its entry. */
    lookup: new Map(variants.map((v) => [v.text.toLowerCase(), v.entry])),
  };
})();

/**
 * The loose hast shape this walker needs. `hast`'s own types do not describe
 * MDX's `mdxJsxFlowElement`/`mdxJsxTextElement` nodes, which are exactly the
 * ones that have to be skipped, so the tree is walked through this instead.
 *
 * @typedef {{ type: string; tagName?: string; name?: string; value?: string;
 *             properties?: Record<string, unknown>; children?: GlossNode[] }} GlossNode
 */

/** @type {import("unified").Plugin<[], import("hast").Root>} */
export default function rehypeGlossary() {
  return (/** @type {any} */ tree, /** @type {any} */ file) => {
    // Lessons only. The glossary page defines these words; linking every one of
    // them to itself would be noise, and /reference is a table.
    const path = String(file?.history?.[0] ?? file?.path ?? "");
    if (!path.includes("/content/lessons/")) return;

    /** One link per term per lesson: the first mention is the one that teaches. */
    const used = new Set();
    const re = PATTERN.make();

    /** @param {GlossNode} node */
    const walk = (node) => {
      const children = node.children;
      if (!children) return;
      /** @type {GlossNode[]} */
      const out = [];
      let changed = false;
      for (const child of children) {
        if (child.type === "element" && SKIP_TAGS.has(String(child.tagName))) {
          out.push(child);
          continue;
        }
        if (
          (child.type === "mdxJsxFlowElement" || child.type === "mdxJsxTextElement") &&
          SKIP_COMPONENTS.has(String(child.name))
        ) {
          out.push(child);
          continue;
        }
        if (child.type !== "text") {
          walk(child);
          out.push(child);
          continue;
        }
        const text = String(child.value ?? "");
        re.lastIndex = 0;
        /** @type {GlossNode[]} */
        const pieces = [];
        let cursor = 0;
        for (let m = re.exec(text); m !== null; m = re.exec(text)) {
          const entry = PATTERN.lookup.get(m[0].toLowerCase());
          if (!entry || used.has(entry.term)) continue;
          used.add(entry.term);
          if (m.index > cursor) pieces.push({ type: "text", value: text.slice(cursor, m.index) });
          pieces.push({
            type: "element",
            tagName: "a",
            properties: {
              className: ["gloss"],
              href: `/glossary/#${glossSlug(entry.term)}`,
              "data-gloss": entry.short,
            },
            children: [{ type: "text", value: m[0] }],
          });
          cursor = m.index + m[0].length;
        }
        if (pieces.length === 0) {
          out.push(child);
          continue;
        }
        if (cursor < text.length) pieces.push({ type: "text", value: text.slice(cursor) });
        out.push(...pieces);
        changed = true;
      }
      if (changed) node.children = out;
    };

    walk(tree);
  };
}
