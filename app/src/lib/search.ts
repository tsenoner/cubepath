/**
 * The /reference filter's vocabulary — one module, because the haystack is
 * built in two places (the tile grid in pages/reference/index.astro and
 * components/CaseRow.astro) and those two copies had already drifted apart.
 *
 * WHY THIS EXISTS. The filter was `haystack.includes(needle)` over
 * `name + recognition + id`. Counted over the 138 entries the built page ships,
 * that returns nothing at all for the things a cuber actually types:
 *
 *     "t perm"      0        "T-Perm"   2      <- the hyphen was load-bearing
 *     "u perm"      0        "4×4"      2      <- so was a × nobody can type
 *     "anti sune"   0
 *     "4x4"         0
 *     "5x5"         0
 *     "awkward"     0        <- though "Awkward Shape (4)" is a heading on the page
 *     "parity"      1 of 3   <- so the 5x5 case reads as missing from the site
 *
 * Three things fix all of it: fold the punctuation the dataset spells one way
 * and readers spell another, widen the haystack to the words the page itself
 * puts on screen (the subgroup heading, the section's own jump label), and
 * match every token of a multi-word query rather than the raw string.
 *
 * NOT the algorithm, though it was tempting and was tried. Adding the moves
 * makes `R U R'` match 136 of 138 cases, which is no more useful than the 0 it
 * returned before — and worse, every alg contains a word-initial "u" and "r",
 * so those tokens stop discriminating for every OTHER query too ("u perm" goes
 * back to matching all 25 perms). The field advertises "name, number or
 * recognition cue"; this searches exactly that, and searches it well.
 */

/**
 * Fold a string to the alphabet a reader types.
 *
 * `×`→`x` (the dataset writes "4×4 PLL", a keyboard writes "4x4"); apostrophes
 * are dropped rather than spaced, so `R'` and `R` fold to one token; everything
 * else non-alphanumeric collapses to a single space, which is what makes
 * "T-Perm" and "t perm" the same two tokens. (That apostrophe rule is for names
 * and cues — the algorithm is deliberately not in the haystack; see below.)
 */
export function normalize(s: string): string {
  return s
    .toLowerCase()
    .replace(/×/g, "x")
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * Everything a case can be found by, normalized and joined.
 *
 * `extra` is for text the PAGE knows and the case does not — the section's jump
 * label ("4×4 parity", "5×5 L2E"). Without it a reader who reads a heading off
 * the screen and types it gets nothing, which is the least forgivable kind of
 * search miss.
 */
export function haystackFor(parts: {
  name: string;
  recognition?: string | undefined;
  id: string;
  group?: string | undefined;
  extra?: string | undefined;
}): string {
  return normalize(
    [parts.name, parts.recognition, parts.id, groupWords(parts.group), parts.extra]
      .filter(Boolean)
      .join(" "),
  );
}

/**
 * A group key as the page prints it: "oll-awkward-shape" -> "awkward shape".
 * Mirrors `subTitle` in pages/reference/index.astro, which turns the same key
 * into the visible `<h3>` — so what the reader sees is what they can search.
 */
function groupWords(group: string | undefined): string {
  if (!group) return "";
  return group.replace(/^(?:4x4oll|4x4pll|oll|pll|f2l|555)-/, "").replace(/-/g, " ");
}

/**
 * Does `haystack` (already normalized) satisfy every token of `query`?
 *
 * AND across tokens — that is the fix that makes "t perm" and "perm t" both
 * find the T-Perm, because the tokens no longer have to appear in the order, or
 * the punctuation, the dataset chose.
 *
 * The per-token rule is length-dependent, and every part of it was measured
 * against the 138 entries the page ships rather than reasoned about:
 *
 *   3+ chars   SUBSTRING. Anchoring these to a word start breaks the two
 *              commonest queries — "light" (35 hits, all inside "headlights"
 *              or "lightning") and "perm" (25, inside "T-Perm") — because
 *              recognition cues are English prose and a reader remembers a
 *              fragment, not a lemma.
 *   1-2 chars  WHOLE WORD when `loose` is false, word START when it is. Plain
 *              substring here is a disaster ("t" is inside almost everything,
 *              so "t perm" matched all 25 perms); but word-start alone is still
 *              too generous, because it also catches the "the", "two" and "top"
 *              in the cues, which is what took "t perm" to 22 measured hits.
 *
 * The two short-token rules disagree about which case they serve, which is why
 * `filter` below runs them in order rather than picking one. "t perm" wants
 * whole-word: the T-Perm's id normalizes to "pll t", so "t" IS a word. "u perm"
 * wants word-start: nothing anywhere is the bare word "u" — the cases are
 * called Ua and Ub.
 */
export function matches(haystack: string, query: string, loose = false): boolean {
  const tokens = normalize(query).split(" ").filter(Boolean);
  return tokens.every((tok) => {
    if (tok.length > 2) return haystack.includes(tok);
    const pattern = loose ? `(^| )${escapeRe(tok)}` : `(^| )${escapeRe(tok)}( |$)`;
    return new RegExp(pattern).test(haystack);
  });
}

/**
 * Which of `haystacks` match — strict first, widening only if nothing does.
 *
 * Exact-then-widen rather than one fixed rule: it gives "t perm" the one case
 * it means and still gives "u perm" the two it means, and it can only ever add
 * results to a query that would otherwise show the empty state. Returns a
 * boolean per input, positionally, so a caller holding DOM nodes can zip it
 * back without building a parallel index.
 */
export function filter(haystacks: readonly string[], query: string): boolean[] {
  if (normalize(query) === "") return haystacks.map(() => true);
  const strict = haystacks.map((h) => matches(h, query, false));
  if (strict.some(Boolean)) return strict;
  return haystacks.map((h) => matches(h, query, true));
}

/** Escape a user-typed token for use inside a RegExp. */
function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
