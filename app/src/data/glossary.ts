/**
 * The site's vocabulary, in one place.
 *
 * WHY THIS EXISTS. This course is written for someone who has never solved a
 * cube, and by the fourth lesson it is using "AUF", "headlights", "F2L" and
 * "slot" in ordinary sentences. Every one of those is defined somewhere — once,
 * in the lesson that introduces it — and a reader who arrives from /reference,
 * from a search result, or three weeks later has no way back to that sentence.
 *
 * Two surfaces read this file and neither restates it:
 *   - `/glossary` renders the whole list.
 *   - `scripts/rehype-glossary.mjs` finds the FIRST mention of each term in
 *     every lesson and turns it into a link to its entry, carrying `short` as
 *     a hover/focus definition. No MDX file is edited, so the glossary cannot
 *     drift out of the prose the way a hand-maintained list would.
 *
 * WHAT BELONGS HERE. A term a reader meets on this site and cannot guess.
 * `tests/glossary.spec.ts` gates two things that keep the list honest: every
 * term must actually appear in a lesson (no glossary of words nobody uses),
 * and every term the printable card set glosses must appear here (the card and
 * the site must not teach different vocabularies —
 * `tools/cubepath/src/cubepath/glossary.py` is the card's copy).
 *
 * `short` is the hover card and is kept to one sentence: it has to be readable
 * in a tooltip on a phone. `long` is the extra paragraph only /glossary shows.
 */

export interface GlossEntry {
  /** Canonical spelling, and the anchor (slugified). */
  term: string;
  /** One sentence. This is what the hover card shows — keep it short. */
  short: string;
  /** Optional second paragraph, shown only on /glossary. */
  long?: string;
  /**
   * Other spellings and inflections that should link to this entry. Matched
   * case-insensitively on word boundaries, longest first.
   */
  also?: string[];
  /** Related terms, by `term`. Rendered as cross-links; gated to resolve. */
  see?: string[];
  /** Where the site teaches it. */
  href?: string;
}

/** Grouped so /glossary reads as a course rather than as an index. */
export interface GlossGroup {
  title: string;
  blurb: string;
  entries: GlossEntry[];
}

export const GLOSSARY: GlossGroup[] = [
  {
    title: "The cube itself",
    blurb:
      "Six faces, twenty-six visible pieces, and three kinds of piece that can never trade jobs.",
    entries: [
      {
        term: "centre",
        short:
          "The single piece in the middle of a face. On a 3×3 it never moves, so it names the face's colour for the whole solve.",
        long: "This is why every recognition cue on this site is written against the centres: they are the one thing that cannot lie to you. On a 4×4 there is no single centre piece — you build each face's centre out of four, which is the first thing that puzzle asks of you.",
        also: ["center", "centres", "centers"],
        see: ["edge", "corner"],
        href: "/learn/cube-anatomy/",
      },
      {
        term: "edge",
        short: "A two-coloured piece between two corners. A 3×3 has twelve.",
        also: ["edges"],
        see: ["centre", "corner", "edge pair"],
        href: "/learn/cube-anatomy/",
      },
      {
        term: "corner",
        short: "A three-coloured piece at a vertex. A cube of any size has exactly eight.",
        long: "An edge can never become a corner and a corner can never become an edge, whatever you do to the cube. That is the unbreakable rule the first lesson is about, and it is why the method can solve one kind of piece at a time.",
        also: ["corners"],
        see: ["centre", "edge"],
        href: "/learn/cube-anatomy/",
      },
      {
        term: "slot",
        short:
          "The place a piece belongs, named by the faces around it — the front-right slot, the UF slot.",
        also: ["slots"],
        see: ["F2L"],
      },
      {
        term: "sticker",
        short: "One coloured square. A corner shows three of them, an edge two, a centre one.",
        also: ["stickers", "facelet", "facelets"],
      },
    ],
  },
  {
    title: "Moves and notation",
    blurb: "One letter, one quarter turn — and the handful of modifiers that go with it.",
    entries: [
      {
        term: "algorithm",
        short: "A fixed sequence of turns you run as a unit to reach a known result.",
        long: "Every algorithm on this site is machine-verified against a cube simulator before it ships, so a wrong one cannot reach you.",
        also: ["algorithms"],
        see: ["trigger"],
        href: "/learn/notation/",
      },
      {
        term: "trigger",
        short:
          "A short algorithm your hands run as one motion rather than as separate letters — the building block bigger algorithms are made of.",
        also: ["triggers"],
        see: ["sexy move", "sledgehammer", "algorithm"],
        href: "/case/beginner.righty/",
      },
      {
        term: "sexy move",
        short:
          "The trigger R U R' U'. This course calls it righty, and the whole beginner method is built from it.",
        also: ["righty"],
        see: ["trigger", "sledgehammer"],
        href: "/case/beginner.righty/",
      },
      {
        term: "sledgehammer",
        short: "The trigger R' F R F'.",
        see: ["trigger", "sexy move"],
      },
      {
        term: "slice",
        short: "A turn of a middle layer, between two outer faces — M, E and S on a 3×3.",
        also: ["slices"],
        see: ["wide turn", "rotation"],
        href: "/learn/notation/",
      },
      {
        term: "wide turn",
        short:
          "A turn that takes two or more layers at once, written lowercase or with a w — r, Rw, 3Rw.",
        long: "Wide turns are what a big cube adds to your notation, and the layer count matters: Rw takes two layers, 3Rw takes three. The 4×4 and 5×5 parity algorithms differ by exactly one such token.",
        also: ["wide turns", "wide move", "wide moves"],
        see: ["slice", "rotation"],
        href: "/learn/444-centers/",
      },
      {
        term: "rotation",
        short:
          "Turning the whole cube rather than a layer — x, y and z. Nothing is solved by a rotation; it only changes what you are looking at.",
        also: ["rotations"],
        see: ["slice", "wide turn"],
        href: "/learn/notation/",
      },
      {
        term: "AUF",
        short:
          "Adjust the Upper Face: the free U turn that lines a case up before you start, or squares the top up afterwards.",
        long: "It is free because it costs one move and never disturbs anything below the top layer — which is why case pictures on this site are not normalised to a single angle.",
        see: ["last layer"],
      },
      {
        term: "regrip",
        short:
          "Moving your hands mid-algorithm to reach the next turn. Fewer regrips, faster solve.",
        also: ["regrips", "change grip"],
        href: "/learn/finger-tricks/",
      },
      {
        term: "conjugate",
        short:
          "Take a piece away, do something, put it back — the shape behind every big-cube centre insert.",
        long: "The setup moves undo themselves, so everything the grab disturbed comes home except the piece you meant to move.",
        also: ["conjugates"],
        href: "/learn/555-centers-edges/",
      },
    ],
  },
  {
    title: "Solving the cube",
    blurb: "The steps every method shares, and the names this course uses for them.",
    entries: [
      {
        term: "cross",
        short:
          "Four edges of one colour placed around their centre, with their side colours matching. The first step of the solve.",
        href: "/learn/white-cross/",
      },
      {
        term: "first layer",
        short: "The cross plus the four corners under it — one whole face and the row beneath it.",
        also: ["first two layers"],
        see: ["F2L"],
        href: "/learn/white-corners/",
      },
      {
        term: "middle layer",
        short: "The four edges between the first and last layers.",
        also: ["second layer"],
        href: "/learn/second-layer/",
      },
      {
        term: "last layer",
        short:
          "The final face and the row around it — the four edges and four corners left when the first two layers are done.",
        see: ["OLL", "PLL", "AUF"],
      },
      {
        term: "F2L",
        short:
          "First Two Layers: solving each corner and its middle-layer edge together as a pair, instead of one layer then the other.",
        long: "It roughly halves your first-two-layers move count and is the single biggest change between the beginner method and CFOP.",
        see: ["first layer", "slot", "look-ahead"],
        href: "/learn/f2l-intuition/",
      },
      {
        term: "OLL",
        short:
          "Orient the Last Layer: make the whole top face one colour, ignoring where the pieces sit.",
        long: "Two-look OLL does it with ten algorithms; full OLL does it in one look with 57.",
        see: ["PLL", "OCLL", "last layer"],
        href: "/learn/two-look-oll/",
      },
      {
        term: "PLL",
        short:
          "Permute the Last Layer: slide the top pieces into their places, once they are all facing the right way.",
        long: "Two-look PLL does it with six algorithms; full PLL does it in one look with 21.",
        see: ["OLL", "last layer"],
        href: "/learn/two-look-pll/",
      },
      {
        term: "OCLL",
        short:
          "Orient the Corners of the Last Layer — the corner half of two-look OLL, seven cases.",
        see: ["OLL"],
        href: "/learn/two-look-oll/",
      },
      {
        term: "orient",
        short: "Turn a piece so its sticker faces the right way, without caring where it sits.",
        also: ["orients", "oriented", "orientation"],
        see: ["permute", "OLL"],
      },
      {
        term: "permute",
        short: "Move a piece to where it belongs, without caring which way round it is.",
        also: ["permutes", "permuted", "permutation"],
        see: ["orient", "PLL"],
      },
      {
        term: "inspection",
        short:
          "The fifteen seconds before the timer starts, spent planning — enough for the whole cross and often the first pair.",
        href: "/learn/cross-planning/",
      },
      {
        term: "look-ahead",
        short:
          "Watching for the next piece while your hands are still finishing this one. Pauses, not turn speed, are where solves lose time.",
        also: ["lookahead"],
        href: "/learn/finger-tricks/",
      },
      {
        term: "scramble",
        short: "A sequence of turns that mixes the cube up, or sets up one specific case to drill.",
        also: ["scrambles"],
        href: "/practice/",
      },
    ],
  },
  {
    title: "Reading a case",
    blurb: "What to look at, and the shapes worth having a name for.",
    entries: [
      {
        term: "headlights",
        short:
          "Two corners on one face showing the same colour, with a different colour between them — a pair of headlights facing you.",
        long: "Headlights are the fastest thing to spot on a last layer, which is why most PLL recognition starts by counting them.",
        see: ["3-bar", "PLL"],
        href: "/learn/two-look-pll/",
      },
      {
        term: "3-bar",
        short:
          "Three stickers of one colour in a row across a face — a solved side of the last layer.",
        also: ["2-bar", "block"],
        see: ["headlights"],
        href: "/learn/full-pll/",
      },
      {
        term: "Sune",
        short:
          "The one-yellow-corner algorithm, R U R' U R U2 R'. The most useful single algorithm in the last layer.",
        also: ["Anti-Sune"],
        see: ["OCLL", "trigger"],
        href: "/case/oll.27/",
      },
      {
        term: "Niklas",
        short:
          "The corner cycle R U' L' U R' U' L: it holds one top corner still and rotates the other three.",
        href: "/case/beginner.niklas/",
      },
      {
        term: "adjacent corner swap",
        short: "The two corners that need to trade places share an edge of the top face.",
        see: ["diagonal corner swap", "headlights"],
        href: "/learn/two-look-pll/",
      },
      {
        term: "diagonal corner swap",
        short: "The two corners that need to trade places sit across the top face from each other.",
        see: ["adjacent corner swap"],
        href: "/learn/two-look-pll/",
      },
    ],
  },
  {
    title: "Big cubes",
    blurb: "A 4×4 and a 5×5 are a 3×3 wearing extra pieces. These are the extra pieces.",
    entries: [
      {
        term: "reduction",
        short:
          "The big-cube method this course teaches: build the centres, pair the edges, then solve the result as a 3×3.",
        long: "Everything you already know is the last step. What a big cube adds is the two steps before it, plus parity.",
        href: "/learn/444-centers/",
      },
      {
        term: "Yau",
        short:
          "A faster ordering of reduction: two centres, the cross, the last four centres, then the edges — so the cross is already done when you reach the 3×3 stage.",
        href: "/learn/444-yau-intro/",
      },
      {
        term: "edge pair",
        short:
          "Two or three edge pieces that behave as one edge once they are joined — what a big cube has instead of a single edge piece.",
        long: "Cubers usually call this a dedge, short for double edge. This site says edge pair.",
        also: ["edge pairs", "dedge", "dedges"],
        see: ["wing", "midge", "reduction"],
        href: "/learn/444-edge-pairing/",
      },
      {
        term: "wing",
        short: "One of the two outer pieces of a big-cube edge pair. A 4×4 and a 5×5 both have 24.",
        also: ["wings"],
        see: ["midge", "edge pair"],
        href: "/learn/444-edge-pairing/",
      },
      {
        term: "midge",
        short:
          "The middle piece of a 5×5 edge group — a true edge piece, which is why a 5×5's last layer obeys 3×3 law.",
        also: ["midges"],
        see: ["wing", "edge pair"],
        href: "/learn/555-centers-edges/",
      },
      {
        term: "freeslice",
        short:
          "Pairing several edges at once by holding a slice out and letting the free layer feed pieces in.",
        also: ["freeslicing"],
        href: "/learn/555-centers-edges/",
      },
      {
        term: "parity",
        short:
          "A state a 3×3 can never reach, but a big cube can — a flipped edge pair, or two edge pairs swapped. It needs its own algorithm.",
        long: "Parity is not a mistake you made. It arrives in about half of all solves, because a big cube's identical-looking pieces let you finish reduction in a position an odd number of swaps away from solved.",
        see: ["reduction", "edge pair"],
        href: "/learn/444-3x3-stage/",
      },
    ],
  },
];

/** Every entry, flat, in the order the page renders them. */
export const GLOSS_ENTRIES: GlossEntry[] = GLOSSARY.flatMap((g) => g.entries);

/** Anchor for a term: lowercase, non-alphanumerics to dashes. */
export const glossSlug = (term: string): string =>
  term
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

export const glossByTerm: ReadonlyMap<string, GlossEntry> = new Map(
  GLOSS_ENTRIES.map((e) => [e.term, e]),
);
