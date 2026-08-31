# Decision log — autonomous build

Decisions made during the autonomous PWA build (Aug 2026), beyond what the
master plan (docs/archive/master-plan.html) and the user's locked answers
specify.
User-locked: full M0–M6 scope · Vercel deploy · push to master per milestone ·
MIT code + CC BY 4.0 content · guide aesthetic · free subdomain · full big-cube
courses · PDF stays first-class.

## Quick-wins phase (guide v0.2)

- **All case diagrams are now derived from algorithms** via the simulator
  (`_derived_*` in diagrams.py), not hand-defined. Rationale: beyond the
  audit's F2/F3, mechanical checking found the shipped Pi diagram depicted an
  H-case rotation, Chameleon's diagram showed diagonal corners for an
  adjacent-corner alg, Bowtie's side stickers were wrong, and all six PLL
  diagrams had physically impossible side colors. Hand-drawn sticker data is
  banned from here on; `tests/test_derivation.py` enforces it.
- **Ua switched to the M-slice variant** `M2 U M U2 M' U M2` (was
  `R U' R U R U R U' R' U' R2`). The simulator proved both have the *identical*
  pre-state (same case, same angle), and the guide's own prose ("Ua, H-Perm,
  Z-Perm all use M") plus Phase 2's "Ua (M-slice version) in Phase 3" promise
  only hold for the M-slice form.
- **H case named "Double Headlights"** (not "H") to match the guide's
  recognition-first naming; the old (wrong) "Headlights" H-picture is reused
  for it, and "Headlights" got a newly derived U-case picture matching its alg.
- **Phase 3 count corrected to +10**: the old "+8" undercounted even before
  the H addition (9 new algs were listed).
- `src/cubepath/algs.py` is the single source of truth for algorithms; the
  guide's tables are tested against it (`test_guide_tables_match_canonical_algorithms`).

## Design phase

- **Static hi-fi mockups** (not clickable prototypes) on the design canvas —
  the product itself is built in code; the canvas exists to react to visual
  direction. Published as "Cubepath UI System"
  (https://claude.ai/code/artifact/a42873c4-ee91-4882-90e5-dbffac7b4fb8).
- **Type**: Newsreader (headings) + IBM Plex Sans (body) + IBM Plex Mono
  (algorithms), all Google Fonts with metric-close fallbacks.
- **Tokens**: warm paper #FCFBF8 / ink #1C1917, accent #1565C0 (the guide's
  algorithm-callout blue), ok #2E7D32, warn #E65100; cube colors and trigger
  colors (trig-r/g/b) carried over verbatim from the pipeline; dark theme
  counterparts defined in the design canvas.
- **Signature elements**: trigger-colored monospace algorithms, real derived
  case diagrams inline, guide callout system on the web, case-row anatomy
  (diagram / name+recognition / alg / status / play).
- The canvas was a one-time exploration. **Retired 2026-08-27**: the design
  system now lives in `app/src/styles/tokens.css`, which is the source of
  truth — the canvas had already drifted past it (its `--line` / `--faint`
  are the pre-contrast-audit values and it never knew about the four
  `--logo-*` tokens). Generator and artboards archived to
  `docs/archive/design/` rather than deleted, because they are the provenance
  for the type and colour choices above.

## M0

- **Worker-safe preload helper**: Rolldown-Vite 8 bundles its preload helper
  (which touches `document`) into cubing.js's search-worker chunk, killing
  on-device scrambles in production builds (vitejs/vite#14499 class;
  `build.modulePreload` doesn't govern worker chunks). Fixed with a small
  Astro `astro:build:done` integration that guards the helper's DOM branch
  behind `typeof document`. The integration throws if Vite's helper shape
  changes, and the Playwright smoke test proves scrambles + both players
  in every build.
- twisty-player uses a **closed** shadow root — E2E asserts rendering via the
  element's own `experimentalScreenshot()` instead of DOM probing.

## Deploys

- During the build, the Vercel **GitHub App was not installed** (interactive
  web authorization required — cannot be done autonomously) and the local
  Vercel CLI token was expired, so milestone deploys went through the
  authenticated Vercel MCP (`deploy_to_vercel`, source-file deploys).
  **Resolved 2026-08-25**: the user installed https://github.com/apps/vercel
  on tsenoner/cubepath; the project is git-linked (root `vercel.json` builds
  from `app/`) and **every push to master now auto-deploys**. The MCP
  file-payload path is retained as a manual fallback, alongside the simpler
  `vercel login && cd app && vercel deploy --prod`. Production alias:
  https://cubepath-six.vercel.app.
  **`scripts/build-deploy-payload.py` deleted 2026-08-27** — it wrote to a
  finished agent session's scratch path, nothing invoked it, and its claim to
  be "the ONLY sanctioned way to assemble a deploy" stopped being true the
  moment pushes started auto-deploying.
- Vercel Deployment Protection (SSO) disabled on the project — required for a
  public PWA and service-worker testing.

## M3

- **JPerm's f2l/2loll/2lpll lib files 404** (verified 2026-08-19:
  jperm.net/lib/{f2l,2loll,2lpll}.js all return HTTP 404), so the 41 F2L cases
  will be sourced semi-manually from JPerm's Best-F2L PDF in M3 (per the
  research brief §8); the extractor covers oll/pll/4x4oll/4x4pll only.

## M5/M6

- **F2L-41 dataset**: JPerm Best-F2L PDF algs mapped to SCDB numbering purely
  mechanically (kpuzzle case-class matching); 14 PDF algs excluded on
  principle (multi-slot or left-slot executions). 105 algs verified.
- **5×5 L2E**: 13 cases (SCDB is right, not 12); invariant allows rigid
  transport of intact non-target edge groups (harmless during reduction);
  4×4-vs-5×5 parity confusion regression-tested.
- **i18n**: v1 ships EN-only; the content collection layout (one MDX per
  lesson, typed data separate from prose) is the i18n-ready structure the
  plan asked for — a locale dimension can be added to the collection without
  restructuring.
- Cheat cards ship both in guide/build (source of truth) and app/public.

## v1.0

- Tagged v1.0.0 at 27761e1 after two full review cycles (/simplify: 18 fixes;
  /code-review: 10 verified findings incl. the unreachable-review-mode bug,
  learned-status clobbering, mirror-chirality step diagrams, and a vacuous
  test gate replaced by real kpuzzle invariants). 487 app tests + 65 python
  tests + 4 E2E green.
- Production deploy was initially blocked on the one-time Vercel GitHub App
  install; the user completed it on 2026-08-25 and v1.0.0 deployed
  automatically from git (see Deploys section above). Live and verified at
  https://cubepath-six.vercel.app.

## Cheat card v2 (2026-08-26, PR #1)

- **Three half-empty cards became one double-sided ID-1 card.** The old set
  used ~50% of its area; the rebuild carries all 15 last-layer cases on the
  front and notation + steps 1–3 + big-cube parity on the back.
- **Two bugs the old card shipped.** Typst smart quotes rewrote every ASCII
  prime to U+2019 (33 curly quotes, zero real primes in the shipped PDF) and
  cubing.js rejects both U+2019 and U+2032 — so no printed algorithm could be
  pasted into a cube tool. And `Courier New` is macOS-only while Typst exits 0
  on an unknown family. Both are now build gates, along with a page-count /
  ink-bbox gate (Typst paginates silently on overflow) and a "no leaked Typst
  markup" gate that was negative-tested by reintroducing the bug it catches.
- **Nothing is retyped.** 3×3 algs expand from `algs.py` via `notation.CHUNKS`
  (22/22 round-trip lossless, coverage-tested); the four big-cube strings are
  read out of the app scripts that pin them for CI, so the card inherits their
  verification.
- **Compact notation, only where provably invertible.** Spaces drop inside a
  chunk, a gap separates chunks. Refused for any alg with a layer-count prefix
  — `2R2 U2` compacted has two legal readings and the wrong one is a different
  cube state. Commutator/conjugate brackets were investigated and rejected:
  10 of 19 algs have no exact decomposition and most that do save 0 characters.
- **Everything typographic was measured at 600dpi, not eyeballed.** The prime
  is boxed at 0.22em pulled left 0.20em (0.38mm before it vs the 0.55mm `R→U`
  letter gap; 1.36mm after vs the 1.31mm `U→F` gap). The regrip gap is 0.55em
  in compacted blocks (4.6× the widest intra-chunk gap) but stays 0.90em in
  the spaced big-cube block, where an ordinary space already measures 1.50mm
  and 0.55em would be 1.03× — inverting the encoding.
- **Palette darkened and unified.** The old triad greyscaled to luma 96/93/88,
  *lighter* than body text, so triggers printed faded. `palette.py` is now the
  one source, drift-tested against `callouts.lua` and the guide's own spans.
- **Vocabulary rule.** Jargon a learner meets elsewhere (sune, headlights,
  OLL/PLL) is taught with a gloss at the point of use; insider shorthand with
  an equally standard plain phrase becomes the plain phrase. "dedge" → "edge
  pair" — which also matched what `444-3x3-stage.mdx` already said. The card
  glosses inline rather than carrying a glossary block: every case row's
  recognition cue defines its own name, so only the bare terms (OLL, PLL,
  parity) needed an explicit line.
- **Printing.** Five PDFs. The A4/Letter imposition is centred so it registers
  under *either* duplex flip; a fold-over variant removes duplex error
  entirely. `docs/printing.md` + a `/print` page. Deliberately skipped: a
  `pypdf /PrintScaling` post-pass and a CR80 press PDF with bleed — neither
  affects home printing and each adds a dependency.

## Card SET — planned, then built (shipped 2026-08-27)

`docs/archive/card-set-plan.md` is the research-backed build order for the staged
card set (3 numbered cards + 1 annex). It has since been executed in full — the
plan is archived, and the sections below are the record of what was decided.
Two load-bearing conclusions:

- **A tier exists only where the learner's ability changes, and after every
  card they must still be able to fully solve a cube.** That kills Phase 1.5
  (it exists only to un-teach the righty-repeat corner twist) and Phase 2
  (two algs plus a reordering).
- **A card stops being a progression card when its completion cannot be
  stated as a solve.** That puts full OLL (57 cases, 22 differing only in a
  sliver) and F2L (no diagrams, no recognition data, not a memorisation
  problem) past the end of the set — they belong in the app trainer.

Prior art (`docs/resources.md`): nothing on the market organises cubing
material by learner stage. The QiYi Secret Tutorial Book is the nearest
neighbour but is a breadth-first 88-page booklet across 14 puzzles, not a
staged pocket set.

### T1 — the 21 PLL algorithms are chunked and measured (2026-08-26)

`notation.pll_rows()` / `pll_algs()` / `PLL_CHUNKS` land the first blocking
task of the card set. Decisions, each with the evidence:

- **Six cases print the guide's string, not JPerm's.** `PLL_OWNED` maps the
  six the guide already teaches back to `algs.py`. Three of the six genuinely
  differ (`Ub` is the R-only alg vs JPerm's `M2`; `H` and `Z` differ in U
  direction and a trailing AUF), so this is a real choice and a test pins the
  divergence set — if it ever moves, someone changed an algorithm.
- **Parentheses become chunk boundaries.** JPerm marks execution units with
  brackets — `(U' D)` in the G perms is the simultaneous double-layer turn,
  `(U R U' R')` in Nb is a trigger. `normalize()` drops them, and a test
  asserts all five bracketed units in the JPerm-sourced cases land on chunk
  boundaries. The annotation survives in the only form the card can print.
- **A rotation always forms its own chunk.** A gap means "change your grip";
  a rotation is the largest grip change there is. Tested for all 21.
- **F, Jb and Na reuse the T perm's middle three chunks** — they contain its
  body, so identical boundaries show the shared work instead of hiding it.

**Measured** (Typst, `--ignore-system-fonts`, DejaVu Sans Mono, 6.5 pt, the
card's `a()` with `GAP = 0.55em`):

- The plan's capacity formula
  `1.3805·chars + 0.5045·primes + 1.2612·(chunks−1)` reproduces the measured
  width of all 21 to **0.00 mm**. It can be trusted for layout arithmetic.
- Widest **Na 43.10 mm**, median 29.91 mm, narrowest **Ua 16.83 mm**.
- Chunk gaps cost **1.261 mm each**, 11.9–20.6 % of an algorithm's width.
- `docs/archive/card-set-plan.md` §3 predicted `F 33.8` / `Na 39.3`; those numbers
  assume **3 chunks per algorithm**. The shipped card chunks at ~3.5 tokens
  per chunk and these follow it, so **three algorithms exceed Card 3's
  33.4 mm text slot, not two**: F (36.32), Na (43.10), Nb (34.31).
- **Wrapping is real and free, verified rather than assumed.** Typst treats
  `h(GAP)` as a break opportunity, so all three wrap at a chunk boundary to
  exactly two lines — 3.94 mm, still under the D = 6.0 mm row pitch. The
  other eighteen stay on one line. No overflow, no Typst warning.

Two things this also settled early: `fullsets.case_state()` resolves all 21
printed algorithms with U correctly oriented, so Card 3's diagrams can be
re-rendered from the exact printed string (the F6 / Z-perm fix); and the
JPerm dataset contains `R3` in one *alternate* Ub algorithm, which `tokenize`
rejects. Legal in cubing.js, unsupported here — harmless while the card
prints primaries, a blocker the day it prints an alternate.

### T2 — card diagrams are re-rendered, not rewritten (2026-08-26)

`diagrams.DiagramStyle` splits the generator into `SCREEN` and `CARD`, and
`cheatcards.build_print_svgs()` now calls the generator instead of running
hex-string substitutions over the finished screen SVGs. The old `_SVG_SUBS`
list is gone.

**Why it mattered.** The substitution list guarded itself with "did every
pattern match at least once", which only catches the day diagrams.py stops
emitting a literal. It could not express a palette at all — it could only
recolour grey and thicken strokes, so the face colours stayed at their screen
values on a card printed in mono. Re-rendering also unblocks Card 3's rule
that a diagram is generated from the exact algorithm printed next to it.

**The palette is measured, not chosen.** `palette.relative_luminance` /
`palette.contrast` (WCAG) are the referee, and `tests/test_diagrams.py` gates
the result. Greyscale contrast, screen → card:

```
red/orange   2.16 -> 4.00   (1.85x)      red/green    1.45 -> 1.96  (1.35x)
red/blue     1.44 -> 2.00   (1.38x)      orange/green 1.49 -> 2.04  (1.38x)
orange/blue  3.12 -> 8.00   (2.56x)      green/blue   2.10 -> 3.91  (1.86x)
yellow/masked 1.28 -> 4.49  (3.51x)  <- the one that made OLL cases printable
```

Every side-face pair improves, and a test asserts that as an invariant rather
than a one-off: a palette edit that makes any pair worse is the wrong edit.
Verified visually in greyscale — at the screen palette an OLL case is ten
identical grey squares; at the card palette the pattern reads at a glance.

**One pair gets worse, deliberately: yellow/orange, 1.64 → 1.42.** It is not
load-bearing. A yellow U sticker never abuts an orange band directly, every
sticker carries a `#333333` outline at stroke width 2.4, and a band is a
different shape from a grid cell. Buying it back would cost the red/orange
separation, which is the pair that appears on *every* diagram (they are
opposite faces) and the one Z-Cube's customers complain about by name.

**Bands widen outward only.** `band_u` 12 → 20 with the inner edge pinned, so
the 192-unit viewBox never moves and every diagram size already measured for
the card still holds. Visible fill goes 0.225 mm → 0.475 mm at D = 6.0 mm.

`SCREEN` keeps integer stroke widths on purpose: svgwrite writes the value
verbatim, so `1.0` would rewrite every committed screen SVG for no visual
change. Confirmed byte-identical output after the refactor.

All four gates were negative-tested — each fails on exactly the regression it
exists to catch (green moved next to red, band narrowed back to 12, masked
grey left at its screen value, card re-rendered in SCREEN style).

### T3 — recognition cues are derived, and three planned claims were wrong (2026-08-26)

`recognition.py` generates every PLL cue from the simulator state the printed
algorithm solves. This was the claim flagged as needing proof before Card 3
was built, because it is the difference between generated-and-testable cues
and 84 hand-written strings labelled machine-verified.

**The load-bearing claim holds.** Counting headlight faces (4 / 1 / 0) →
(edges only / adjacent swap / diagonal swap) reproduces JPerm's own `group`
field for **all 21**, including the three cases where the card prints the
guide's algorithm instead of JPerm's. And the corner facts alone separate 19
of 21, with exactly the two predicted collisions — `{H, Z}` and `{Ua, Ub}` —
settled by the edge cycle. Cues and signatures are 21/21 unique.

**Three planned claims were wrong. Each was caught by testing it first.**

1. **There is no "minimal clause set unique among the 21".** Recognition is
   closed-world. `Ga` is exactly `L headlights + F pair`; `Aa` is that *plus*
   `R pair`, so every subset of Ga's facts is also true of Aa. Ten of the 21
   have no identifying positive subset — F, Ra, Rb, Ga–Gd and the four
   edges-only cases. A cue must state the whole signature.
2. **`CUE_MAX_CHARS` is 51, not 34.** Measured in Typst at Libertinus 4.0pt:
   the widest glyph across the real cues is 0.6424 mm, so 33.4 / 0.6424 = 51
   is safe even for a cue of nothing but the widest character. The widest real
   cue (Ua, 48 chars) measures 26.97 mm — 81% of the slot. A cap of 34 would
   have forced hand-abbreviated cues for no reason.
3. **A matching pair does not mean "that corner is home".** 14 of the 30 pairs
   violate it: a pair is a corner facelet matching its neighbouring edge
   facelet, which happens with both pieces wrong. This was tested before any
   cue depended on it, so nothing shipped on it.

**Cue wording is pinned to the renderer's geometry.** A pair is named by face
and by which end of that face's strip it sits at (`F-left`, `R-back`), because
"left" on the right-hand strip is meaningless to a reader. The plan's own fact
table differs from the derivation by a systematic flip on R and B — a strip
reading-direction convention, not an error, but exactly the ambiguity that
makes hand-written cues unsafe.
`test_strip_reading_order_matches_the_drawing` renders a probe diagram with a
unique colour per sticker and reads the coordinates back, so inverting a strip
in `diagrams.py` fails the build rather than silently pointing every cue at
the wrong end.

**Card 2's Sune promise is measured.** BFS over `{∅, U, U2, U'} × Sune`
reproduces `{Sune 1, Anti-Sune 2, Pi 2, Headlights 3, Double Headlights 2,
Chameleon 3, Bowtie 3}`, max 3 — which is what licenses "at most three Sunes"
in print. And Niklas really does wreck the yellow face, per the simulator.

All four new gates negative-tested: reverting the 3-cycle direction
derivation, printing the edge clause on every case, mis-stating the headlight
count, and inverting a strip's drawing order each fail exactly their own test.

### T4–T8 — the card set is built (2026-08-27)

Four ID-1 panels: three numbered progression cards and one annex, from
`cards.py` (content) + `cheatcards.py` (imposition and gates). The single-card
v2 is replaced. Entry point is `cubepath-cards`; `cubepath-cheatcards` and
`make cheatcards` stay as aliases.

**The gate that mattered most was one the plan did not specify.** A card is a
fixed-height box, so when its content overruns it does **not** paginate — it
silently overlaps its own footer. The page-count gate cannot see that, and the
first render shipped Card 3's glossary printed on top of its own map footer.
`fit()` now measures the real rendered height inside Typst and refuses to
compile. It caught four separate overflows during the build, including two the
plan's own arithmetic said were fine. Measured heights of the 49.98 mm budget:

```
first-solve  46.76 / 42.48      two-look      48.20 / 49.16
one-look-pll 44.82 / 49.16      annex         31.73 / 29.47
```

Related: the footer is now a block in the flow, not `place(bottom + left, …)`.
Placed absolutely it grows *upward* into the content, which is how a four-line
footer collided with a glossary that fit perfectly well on its own.

**Vocabulary is enforced against the rendered PDF, not by proofreading.**
`glossary.py` splits terms three ways: `TEACH` must carry its gloss on *every*
card that uses it (a term defined on Card 1 is forgotten by Card 3, and the
annex is the card people cut off); `DEMONSTRATED` terms are defined by the
footer legend printing the swatch, the literal algorithm and the name together,
which beats any six words; `BANNED` terms fail the build with their
replacement named. The gate found four real violations, one per card.

Two extraction subtleties this exposed, both fixed in the test rather than by
distorting the card: `pdftotext` drops the hyphen when a compound wraps at it
(`corner-and-edge` → `corner-andedge`, `look-ahead` → `lookahead`), so the
gloss check compares on letters alone; and Typst reads `______` in a write-in
blank as emphasis markup, which it only *warns* about — and warnings are fatal
here, so it surfaced instead of silently italicising the card.

**Other corrections found by building it:**

- **Phase 1.5 adds one algorithm, not zero and not three.** The guide said
  "No new algorithms"; the plan said "+3". `algs.py` says the wide-`f` Hook is
  new there and nothing else is, and the guide's running total stopped at ~18
  for a 22-algorithm set. The progression table is now derived and tested.
- **What's Next now puts full PLL before full OLL**, with the reason printed:
  PLL is a closed set of 21 states told apart by sight; 22 of the 57 OLL cases
  differ only by a sliver at card size.
- **Annex big-cube algorithms need full card width.** They keep real spaces (a
  layer-count prefix makes compaction ambiguous), so an 18-move parity
  algorithm wrapped to two lines in a 40.2 mm column. Card faces are now
  composed from full-width and two-column sections.
- **`Row` is a dataclass, not a tuple.** A Sune badge smuggled into the `name`
  field had its `#` escaped and printed as literal Typst source on the card.
  Prose and markup are now separate fields.

**Duplex.** Two files per paper size, one per flip, and deliberately never one
file claiming to work under either: a whole-page 180° rotation alone
degenerates into the long-edge column swap and pairs Card 1's front with
Card 2's back. That is invisible on a sheet of identical cards, which is how it
survived in the single-card build. The row-duplication theorem
(`FRONT_SLOTS[2k] == FRONT_SLOTS[2k+1]`) is asserted at build time, along with
both permutations being involutions and `σ_short == ρ ∘ σ_long`. Mirror
identities use `abs(…) ≤ 0.01`, never `==`.

**`/c0`–`/c3` are a permanent public contract.** They are printed on card
stock; a printed card cannot be redeployed. Playwright asserts all four return
200 and name their own card. The app renders them from `manifest.json`, so the
web ladder is the deck table rather than a second copy of it.

**Playwright port.** A parallel `astro dev` on 4321 was being reused by
`reuseExistingServer`, and the dev toolbar injects its own `<h1>` elements —
breaking every heading assertion for reasons unrelated to the app. `PW_PORT`
moves the test server out of the way.

## Card set — shipped (2026-08-27)

Closes the only completed item that was still filed in `docs/TODO.md`: the
request for "small portable credit-card size cheatsheets for each step",
modelled on the [Z-Cube CFOP card
set](https://mastercubestore.de/anleitungen-ratgeber/1923-z-cube-cfop-cards-algorithm-set-f2l-oll-and-pll.html).

Shipped as the four-card progression set — three numbered cards plus an annex.
`make cards` generates them from the canonical algorithm data into
`guide/build/cards/` and syncs the PDFs to `app/public/cards/`; the app serves
them from `/print` and from the frozen per-card routes `/c0`–`/c3`. Why the set
stops at three cards is in `docs/archive/card-set-plan.md`; print, duplex and
lamination guidance is in `docs/printing.md`.

Deliberately *not* a copy of the prior art: the Z-Cube set is organised by
algorithm family (F2L / OLL / PLL), this one by learner stage, so finishing any
card still leaves you able to solve the whole cube.

## Notation overview — redrawn (2026-08-28)

`guide/figures/generated/notation/overview.svg` was a flat three-quad block with
a spike out of each face centre and a ~280° ribbon ring around it. The idea —
a pin per face, its letter at the tip, its turn around the pin — was right,
and the user liked it; the drawing was not. At the two shipped sizes (272 px
in the PDF, 360 px in the app) the rings were unreadable, the 1×1 block read
as a whole-cube rotation, both consumers' captions called it "the x, y, z
rotation axes", it was the one diagram that derived nothing, its only gate was
"the file exists", and a layout commit (`817b7d1`) had evicted it from the
Notation section to the last line of the PDF.

**Shipped: the pins, drawn to read.** Same idea, same 3D ribbon geometry (the
band around the axis, split around the pin, the arrowhead in the band's own
plane — `_ribbon_arc` is the original code with parameters), with what made
it unreadable fixed: ring radius 0.72 stickers instead of 0.6, a 250° sweep
instead of 280°, a larger head, faint layer lines on the cube so it is a
3×3 and not a block, and the six tips at two derived screen radii so the star
is balanced and compact (183 × 183 units against 226 × 231). Dots at the
tips and the letters just beyond them, as before. The arrowhead's position on
each ring is derived from the view direction. Six face turns only.

**Kept as backup: the F hub** (`overview_hub.svg`). F spins as a ring in the
middle of the front face and every other letter slides its layer along an
edge of a face you can see — the turns as seen from your seat — with the
strip directions derived by marking the strip on a solved cube and applying
the move. Rendered and committed beside `overview.svg` — so the byte-identity
gate and the 131 count cover it, and the app serves (and precaches) it at
`/diagrams/notation/overview_hub.svg` — but referenced by no lesson, guide
page or card; one filename swap away.

**Tried and dropped, recorded so it is not retried.** A first redesign put
all nine layer turns (faces plus slices) on one cube — arcs on the visible
faces, hooks over the edges — with a small dashed cube for x / y / z and three
micro cubes for the modifiers. Correct and gated, and judged by the user
*more* confusing than the pins: three arrow idioms on one cube and labels far
from the arrows they named. On this cube anything beyond the six face turns
needs a second idiom, and the fifteen move diagrams sit right below.

**Gates.** The rings must pass their face's edge-middle stickers in the order
one turn of that face carries a sticker (simulator-checked for the visible
faces; the ring basis is proven clockwise-from-outside for all six); pins
start at the face centre, run along the normal and land at the layout's
screen radius; every arrowhead's tip in the SVG is the projected end of its
ring; a dot is painted under every ribbon vertex it meets on screen that is
nearer the camera and over every one that is farther (B's dot used to sit
on top of its own ring); the hidden faces' ribbons — both band edges, the
head and half the stroke — clear the cube's silhouette (the centre line
alone once passed while B's inner edge was a tenth inside it); every letter
is present once and sits on the plate so it flips with the theme; the
computed frame holds every coordinate and label, in both layouts and both
palettes; the committed SVGs match the generator byte for byte. The hub
keeps its own gates (strip directions re-derived independently of the
renderer, reverse reading false, letters nearer their own arrow than any
other, card halo by `palette.contrast`).

**Theme and card.** A review found the pins tagged `.ink`, a rule on `fill`
that does nothing to a `<line>`, so on a dark page the six dots and letters
flipped and the pins stayed `#222222` on `#161412` (1.15:1) — inherited from
the old figure, whose axis lines were never tagged, but load-bearing once
the figure led the lesson. The ribbons' literal white fills glared the same
way. `_THEME_CSS` now flips three classes: `.ink` (fills), `.ink-stroke`
(plate strokes: the pins' plate runs, the ribbons' edges and caps) and
`.paper` (the ribbons' occluding fill; its dark value is pinned to
`tokens.css`, because an occluder only works if it is the page). A
visible face's pin is split where it leaves its face, because its on-face
run must stay dark against the sticker; on the annex card that run gets the
same paper rim the hub's arrows get, measured by `_ov_needs_halo` — the
card's red is 1.97:1 against the ink and the F pin used to cross it bare.
Gated: nothing white on the pins' plate but `.bg` and `.paper`, every plate
line `.ink-stroke`, one rim per on-face run in `CARD` and none on screen.

**Placement.** Back in `# Notation` in the guide (a one-cell borderless
table, so it centres without pandoc's captioned `#figure` wrapper — the old
figure was the PDF's only "Figure 1"), at the top of the app's notation
lesson as the map the sections then detail, and on the annex card beside the
notation key in card ink.

Larger question filed, not acted on: [#2](https://github.com/tsenoner/cubepath/issues/2),
whether the generator should move to TypeScript on cubing.js so the repo has
one cube model instead of `cube.py` plus kpuzzle.

## Python vs JS/TS — no migration; JS becomes the cube's source of truth (2026-08-27)

The question was asked plainly: where do we need Python, could most of it be
JS/TS, and would that be better? Answered by a structured decision — two survey
agents establishing facts, three advocates arguing keep / move / hybrid, and a
judge instructed to discount any advocate who concealed a weakness.

**Nothing in this repo requires Python.** 4,897 lines across 12 modules with
exactly one third-party runtime dependency (`svgwrite`, imported by
`diagrams.py` alone); pandoc, typst and poppler are external binaries invoked
by subprocess, so the PDF path is indifferent to what calls it. Feasibility was
never the question.

**Python stays anyway, for two things.** 1,255 lines of hand-written SVG
geometry — the isometric cube views and the logo — have no replacement in the
JS cubing stack: `twisty-player`'s strategies all route to three.js/WebGL,
`SVGRenderer` appears nowhere in cubing's dist, and
`PuzzleGeometry.generatesvg(threed:true)` rasterises to a degenerate collapsed
net. And 1,781 lines of Typst/card generation is string templating and
imposition algebra that would be translated for zero gain. A full port was
measured at ~7,429 lines retyped to delete ~730, with 241 of 287 assertions
having nowhere to go.

Worth recording because it was the strongest argument on the other side, and it
was *true*: the judge independently reproduced 68/68 arrow-free plan-view SVGs
byte-identically from a 40-line zero-dependency JS emitter in 14 ms. Portable is
not the same as worth porting.

**But the boundary moves.** `cube.py` was silently mis-simulating big-cube
algorithms — the standard 4×4 OLL-parity alg parsed, raised nothing, and
returned a meaningless 3×3 state. Root cause was structural rather than a
missing branch: `parse_algorithm` was `_TOKEN_RE.findall(alg)`, which by
construction discards every character it cannot match. 62 of the 104 approved
new diagrams are big-cube, so the failure mode was a plausible-looking wrong
picture — unacceptable in a repo whose value is the correctness of algorithm
data.

So: **JavaScript is the single source of cube truth; Python reads JSON and
draws.** cubing.js already ships 4×4×4 and 5×5×5 kpuzzles and this repo already
consumes them. This generalises the existing `jperm-raw.json` pattern rather
than inventing a new seam. `cube.py` is demoted to a gated 3×3 mirror: its
parser now consumes the whole string and raises on any token a 3×3 cannot model,
and `tests/test_conventions.py` machine-checks that its docstring still says so.

**Do not write a 4×4 or 5×5 simulator in Python.** That is the duplicated
cube-model mistake made a second time and larger. This is the rule the next
contributor is most likely to break, which is why it is written here.

## 4×4 parity-embedded cases: locked, not deleted (2026-08-28)

The app shipped 49 generated 4×4 cases in two sets (`4x4oll-*`, 27;
`4x4pll-*`, 22), presented in the trainer as "4×4 OLL + parity" and "4×4 PLL +
parity" and in `/reference` as two grids. Both names were wrong, and the sets
did not belong in a course that teaches 2-look OLL/PLL.

**The measurement.** Reproducible from `app/src/data/extracted/jperm-raw.json`:
**27 of 27** `4x4oll` algorithms contain the OLL-parity algorithm
(`Rw U2 x Rw U2 Rw U2 Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'`) verbatim, and
**22 of 22** `4x4pll` algorithms contain the PLL-parity algorithm
(`2R2 U2 2R2 Uw2 2R2 Uw2`) verbatim. `gen-case-states.mjs` had already recorded
the same fact in `case-states.json` (`parityAlgs[*].signature`). They are not a
separate 4×4 OLL/PLL system: each one is a 3×3 last-layer algorithm with the
parity fix spliced into it — a one-look optimisation for solvers who already
know full OLL and PLL. The name "OLL + parity" read as "the OLL set, plus a
parity case"; the contents were the opposite.

**Three stay.** `444.oll-parity` (curated), `444.pll.pure-e` — whose algorithm
*is* the bare PLL parity — and `444.pll.adj-e`, which the 4×4 lesson teaches as
parity's second face. The lesson's own closing section already said 2-look plus
these three finishes any 4×4; the other 47 contradicted it by sitting in the
reference as if they were course material.

> **Superseded 2026-08-28** — it is two, not three. `444.pll.adj-e` was locked
> alongside the other 47; see "§ The 4×4 taught set is two algorithms" below.

**Locked, not deleted**, because the work is correct and finished: the 49 cases
stay in `jperm-raw.json` and the generated fullsets, all 220 diagrams stay
generated and gated, and `tests/algs.spec.ts` keeps machine-verifying every
hidden algorithm. Deleting them would throw away verified data to solve a
presentation problem, and the user asked for exactly this: hide now, "we could
make them unlock later".

**The one line to flip** is in `app/src/lib/unlocks.ts`:

```ts
export const UNLOCKED: Record<UnlockKey, boolean> = {
  "444-parity-embedded": false,   // -> true
};
```

Everything else asks the single predicate `isLocked(caseOrGroupKey)` exported
beside it — the trainer's set list, pool and counts (`lib/trainer.ts`), the
`/reference` sections, and `getStaticPaths` in `pages/case/[...id].astro`.
Nothing re-derives the rule, so unlocking cannot half-happen.
`app/tests/unlocks.spec.ts` gates both directions: with the flag off no locked
case is reachable from any pool, set list, count or `?group=` deep link; with it
on, exactly 47 more cases appear and nothing outside the 4×4 sets moves.

**The trainer sets** are now one honest visible set, `444-parity` ("4×4
parity", 3 cases), with `444-oll` / `444-pll` kept defined but filtered out and
renamed "4×4 OLL (parity-embedded)" / "4×4 PLL (parity-embedded)" for the day
they come back. The 4×4 lesson's `practice.groups` points at `444-parity`, and
its closing paragraph keeps the explanation of what parity-embedded cases are
but no longer sends the reader to `/reference/` to find "the full
parity-embedded case sets", which are not there any more. (It never carried
`#444-oll` / `#444-pll` anchors — the old copy linked to `/reference/` plain —
so the change broke no anchor; a whole-site crawl of the built output finds
zero dead links and zero dead fragments in both flag states.)

**Locked cases get no `/case/` page.** 138 case pages build instead of 185.
Building the 47 would have recreated the defect this repo was already pulled up
on — case pages reachable from nowhere — and here they would also have been
listed in the sitemap and precached into every visitor's service worker
(~23 KiB each, ~1.0 MiB of pages for a set the lesson tells you not to learn
yet). The cost accepted in exchange is that those 47 URLs 404 while locked;
they were linked from nowhere on the site, so no internal link breaks, and the
same predicate restores them unchanged when the flag flips. Verified after the
change: the sitemap lists 171 URLs, of which the only `/case/444.*` entries are
the taught cases (three at the time; two since 2026-08-28).

## The three-tier colour model, and the audit that found it unwired

**The model.** Every diagram on the site — 3D player or static SVG — puts each
facelet in one of three tiers: **full colour** for what this step solves, **dim**
for what an earlier step already solved and must be preserved, **grey** for what
the method has not reached. The alternative was cubing.js's stock two tiers
(highlight / dim), which cannot say the third thing at all. On the white-corners
lesson that difference is the whole lesson: the learner has to see the white
cross held DIM while the corner in hand is lit, and everything above it dark.

The ordering lives in `app/src/data/extracted/stages.json`
(`cubepath/stages@2`), generated by `app/scripts/gen-stickering.mjs` out of
cubing.js by layer-move algebra — no slot index is ever typed — and read by
`app/src/lib/ladders.ts`. Three properties are load-bearing: there are TWO 3×3
ladders (beginner permutes the last-layer edges before orienting the corners,
CFOP orients first), so a tier cannot live on `CaseDef`; "done" is not a boolean
for a last-layer piece, so every stage carries an aspect and the mask narrows on
that aspect alone; and a centre is never grey, because it is the frame every
recognition cue on the site is written against.

**What the four-agent adversarial audit found (Aug 2026).** The ladder was
CORRECT — every stage's piece set re-derived from the kpuzzle matched
byte-for-byte — and NOT WIRED TO ANY RENDERER. `TwistyPlayer.astro` called
`maskFor(puzzle, stickering, alg)` with three arguments; there was no `context`
prop, and `contextForCase` had zero non-test callers. **0 of 185 cases rendered a
ladder mask.** Every test passed, because every test called the functions
directly and never looked at the rendered output.

That is the finding worth keeping. A test that exercises a function while the
renderer calls something else gates nothing. Everything asserted about tiering
now reads either the rendered `experimental-stickering-mask-orbits` attribute
(`tests/algs.spec.ts`, via the Astro container) or the shipped HTML in a browser
(`e2e/stickering.spec.ts`, page list taken from the sitemap so it is every route
the build publishes). `e2e/stickering.spec.ts` checks all 138 built case pages.

**The same class of bug, one level down.** A case state is a PRE-state
(`solved · alg⁻¹`), so a net whole-cube rotation the algorithm carries sits on
its LEFT — `scripts/lib/kpuzzle-utils.mjs` says exactly that in its own doc
comment ("Using the wrong side conjugates the state onto the wrong faces") and
exports `leftRotNormalize` for it. `stickering.ts` cancelled the rotation on the
RIGHT instead. Both orders bring the centres home, so the search succeeds and
nothing looks broken; they simply answer about different cubes. 27 of the 185
cases carry a net rotation (18 F2L, 5 PLL — Aa, Ab, E, Ja, V — 2 5×5 L2E, 2
locked 4×4 PLL), and all 25 of them with a page shipped a mask on the wrong
pieces: `pll.aa`, a pure three-cycle of U corners, lit ONE corner, two of the
three it should have lit having been reported in the BOTTOM layer; the 18 F2L
cases lit a different slot from the other 23, though all 41 are the FR slot.

It survived review because the test shared the implementation's mistake —
`tests/algs.spec.ts` normalized the same pre-state with `normalizePattern`,
which is the right-composing one. Fixed on both sides; `caseStateOf` in the test
file now left-composes, and 51 tests fail if the implementation regresses.

**Two greys, deliberately different tones.** A grey sticker meant two
incompatible things across the shipped SVG set. On an OLL plan view it means
"this facelet is a real sticker that is not yellow" — read its ORIENTATION. On a
step or F2L diagram it means "the method has not REACHED here". They meet on one
page (`yellow-cross.mdx` prints `step_4_ycross` above the three OLL cross
cases). The orientation mask keeps `#C0C0C0` to the byte — 95 shipped plan views
are built on it and it is what every OLL reference draws — so the tier that
moved is the other one: `UNREACHED`, then `#C0D4E6` and 13.1 ΔE away. No single
SVG may contain both, and `tests/test_diagrams.py` measures it. (That tone is
`#D8D5CF` now, 8.3 ΔE away, and the gate moved down with it — see § "The
not-reached grey is warm, not blue" for why 13 was buying nothing here.)

**Contrast, and which metric.** Only the SVG palette is ours: cubing 0.63.3 has
no cube-palette API. `ladders.ts` tabulates the player's failures in WCAG
contrast, which is a luminance-only metric built for text; on that measure seven
3×3 tier pairs fall under 2:1, worst orange D:grey at 1.09. Ranked by CIE ΔE —
the metric that decides whether two adjacent PATCHES read as different — the
order changes completely: orange D:grey is 51.8 ΔE, plainly two different hues.
The one genuinely marginal pair is **white highlight vs white dim, 11.9 ΔE**,
the only pair with no hue to separate it. It does not in fact reach the screen:
`SETUP_ALG` points the white face down, and a piece in the dim tier is a solved
first-layer piece whose white facelet is therefore on D. Both metrics are worth
quoting; quoting one as if it were the other is not.

The SVG side was tuned against ΔE for that reason. `diagrams.dim()` is a Lab
transform — same hue, chroma × 0.32, an L\* step away from a pivot so light
faces darken and dark faces lighten — sized so the minimum ΔE(full, dim) is
**30.0** across both the screen and card palettes (the linear mix it replaced
managed 15.1, on white, which has no chroma to spend). The shared artifact
between the two renderers is stages.json's TIER ASSIGNMENT, never the colours.

**Still open.** Five case pages display with the U face tipped off the top —
`pll.aa`, `pll.ab`, `pll.e`, `pll.ja` (an `x`/`x'` in the algorithm) and
`555.l2e-12`. That is not a mask fault: the mask binds to the cubie and is
correct on all five. It is that `experimental-setup-anchor="end"` plays the
algorithm backwards including its net rotation, so the case state is shown
rotated. Twenty more cases spin about `y` only, which is benign — the pair still
reads at the front-right. Fixing the five means folding the net rotation into
`experimental-setup-alg`, which is a camera decision, not a stickering one.

## The 4×4 taught set is two algorithms, not three (2026-08-28)

The user asked why the course needs `444.pll.pure-e` when J Perm's 4×4 tutorial
teaches an edge flip, an OLL parity and a PLL parity — guessing that our
`444.pll.adj-e` was that PLL parity. It is the other way round, and the
measurement is unambiguous: **`444.pll.pure-e`'s primary IS J Perm's PLL parity**,
`2R2 U2 2R2 Uw2 2R2 Uw2`, byte-identical to the string in his video description,
`isIdentical()` true on the cubing.js 4×4×4 kpuzzle. `444.pll.adj-e` is a
different transformation — the same algorithm with a U-perm fused around it.

**Adj-E is locked**, verified redundant rather than assumed. Taking its case
state and searching `[AUF] parity [AUF] <one of the 21 verified PLL primaries>
[AUF]` found four exact solutions to a solved cube (e.g. `parity, U', Ub, U'`),
and Pure-E is solved by the bare parity algorithm with no AUF at all. So J
Perm's rule holds as stated in his transcript at 9:01 — run parity once and an
ordinary PLL is what remains. Adj-E bought one look and cost a fourth
algorithm: the same trade the other 47 are locked for, so it is locked on the
same rule. The taught set is now exactly the two algorithms the video teaches.

**The parity algorithm's corner action is exactly `U2`.** Measured on solved it
displaces four corners and four wings; `T("U2")·T(pure-e)` displaces zero
corners and four wings. So it is a pure opposite-dedge swap once the free AUF is
folded in — which is what lets J Perm describe it as swapping "this front piece
with this back piece".

**Consequence worth recording:** the case state is derived as a bare
alg-inverse with no AUF normalisation, so `444_pll_pure_e.svg` draws that `U2`
corner displacement on top of the edge swap, while the extraction's group label
called it "Edges Only". The state is a legitimate representative and the
algorithm does solve it as drawn, so the derivation is left alone — rotating the
stored state would desync the SVG from the `<twisty-player>`, which derives its
own state from the algorithm and would still show the unrotated one. Fixed
instead where it was actually wrong: `gen-cases.mjs`'s big-cube branch now
honours `recognition.json` (it hardcoded the group label and bypassed the lookup
the OLL/PLL branches use), and the lesson names the `U2` outright.

## 4×4 trainer scrambles never produced their case (2026-08-28)

Found while deciding the above, unrelated to it, and shipped broken: **all 196
trainer scrambles under `444.*` were outer-layer moves only** — zero slice or
wide moves in any of them. Outer turns carry both wings of an edge together, so
from a reduced cube they cannot produce either parity. Every one set up an
ordinary 3×3-legal state rather than the case it named, which means a learner
drilling `444-parity` never met the parity case.

It survived because the gate that would have caught it —
`algs.spec.ts`'s "one verified scramble per 3x3 case is solved by its primary
alg" — skips anything that is not `3x3x3`, while `gen-cases.mjs` wrote the
comment "Verified per-case trainer scrambles (each produces its case)" that
nothing checked. The extraction's scrambles were authored for a 3×3 renderer and
were never valid for these cases.

**Fix:** `gen-cases.mjs` no longer emits big-cube scrambles, so
`setupScramble()` falls back to inverse-of-alg with a random AUF, which is
correct for any puzzle. Two new assertions pin it: no big-cube case ships a
scramble, and every scramble that does ship belongs to a case the 3×3 gate
actually checks — so a scramble can no longer ship unverified by being a puzzle
that block skips.

## One diagram tree, not two (2026-08-28)

The 221 SVGs were committed **twice** — `guide/figures/generated/` for the PDF
and `app/public/diagrams/` for the site — kept in step by
`scripts/sync-diagrams.sh` and a byte-identity test whose only job was to prove
the copy had run. `docs/TODO.md` carried this as open work; an earlier attempt
prototyped a git-tracked symlink, a top-level `diagrams/`, and a `build.sh`
rework, and was abandoned uncommitted.

**`app/public/diagrams/` is now the only tree.** The app is the one consumer
that must serve these from a fixed URL, so it owns them; `cubepath-diagrams`
writes there directly, and `guide/cubepath.md` reaches up with
`../app/public/diagrams/…`.

**`--root ..` in `guide/defaults/pdf.yaml` is load-bearing**, which is why it
carries a comment: typst sandboxes file reads to its project root and rejects
every `../` path without it. Pandoc cannot rewrite the paths for us, because
`filters/callouts.lua` emits raw `#image()` markup for rotated figures that
pandoc never sees as images.

**Verified, not assumed:** all 9 pages of the rebuilt PDF rasterise
sha256-identical at 60 dpi to the pre-change build. The change is invisible in
the output, which is the only acceptable result for a pure de-duplication.

The byte-identity test had nothing left to compare and was replaced by the gate
that matters now — the guide's figure paths all resolve, `figures/generated`
appears nowhere, neither the second tree nor `sync-diagrams.sh` has come back,
and `pdf.yaml` still passes `--root ..`. Tracked files drop by 221.

## The 5×5 course is two algorithms and one technique (2026-08-28)

The user asked to orient the 5×5 on J Perm's beginner tutorial, naming three
things to learn: switching a centre piece, switching the edges, and the edge
parity algorithm — then corrected the first: *"the 3rd alg to switch Centers
isn't a proper alg. It is more a learned approach."*

**That correction is the source's own framing.** The transcript, at 3:15:
*"make sure you remember this whole pattern — it's not necessarily one
algorithm, but this pattern will apply no matter which pieces you're trying to
move into here."* There is no centre algorithm anywhere in the video. So the
honest count is **two algorithms plus one technique**, and the lessons now say
so in those words.

**The two algorithms**, both verified on the cubing.js 5×5×5 kpuzzle and both
byte-identical to the strings in the video's description:

- edge flip `R U R' F R' F' R` — turns one edge group over in place. Outer
  turns only, so it cannot break a finished pair, and it means literally the
  same thing on a 4×4. J Perm says as much at 4:15.
- edge parity `Rw U2 x Rw U2 Rw U2 3Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'` —
  already shipped. Works at exactly one hold, UF: tested against the same state
  at UB, UR, FR and DF, where it does not solve.

**The cut is safe, and it is proved rather than deferred to.** Every outer-turn
algorithm — the flip included — induces an EVEN permutation of the 24 wings,
and conjugating by a slice preserves parity, so no amount of slice-flip-slice
can ever reach an odd state. The parity algorithm is the one ODD generator.
That makes the two not merely sufficient by convention but exactly the two
generators the puzzle requires. `verify-l2e.mjs` now asserts that argument —
outer turns and the flip EVEN, the flip conjugated by Uw/Rw/3Rw/Lw'/Uw2 EVEN,
the parity algorithm ODD — so it is a regression test, not a paragraph.

What is lost is speed at last-two-edges: the 13-case set is a one-look
optimisation, replaced by an iterative loop of slice-flip-slices. A time cost,
never a can't-finish cost. Twelve cases are **locked, not deleted**, on the
same mechanism and for the same reason as the 4×4 set.

**What is verified, and what is not.** The NECESSITY half is a proof and is
pinned: parity cannot be reached or removed by any amount of pairing, so the
parity algorithm is required. The per-case half is measured and pinned too —
8 of the 13 are odd (l2e-5,6,7,8,9,10,11,12), every alternate algorithm of a
case agrees with its case's parity, and one parity application clears every odd
case, so parity is the only obstruction the flip cannot pass.

The SUFFICIENCY half is weaker than a planning agent first reported. It claimed
all 13 fall to at most three slice-flip-slice macros; searching an 850-macro
vocabulary to depth 2 reproduces that for only 7 of them (l2e-1, 2, 6, 8, 9,
10, 11). The remaining six may need a third macro, a different aiming vocabulary
or a better search — not established either way. A lesson sentence briefly
said "at most three rounds finishes any case — that is measured, not an
estimate"; it was not, and it has been corrected to claim nothing about a round
count. **Nothing about the course changes:** what makes the cut safe is the
necessity proof plus the fact that the flip is the standard pairing tool, not a
bound on how many times a learner fires it.

**Three defects fell out of the work, all shipped:**

1. `555.l2e-6` printed the SCDB primary, so the lesson's "open 444.oll-parity
   and 555.l2e-6 side by side, they are near-twins" instruction compared two
   different algorithms of different lengths. `verify-l2e.mjs` now pins J
   Perm's string as `algs[0]`; all four solve the same case and the EXPECT
   profile is identical across them, so the reorder is inert to every check.
2. All thirteen carried the same hardcoded recognition string, because the 555
   branch of `gen-cases.mjs` bypassed the `recognition.json` lookup the other
   branches use. With no 5×5 diagrams, `/reference` rendered thirteen
   identically-labelled tiles nobody could tell apart — which is an independent
   reason the twelve could never have been drilled.
3. The cheat card's `l2e-flip` read `l2e-1` out of `l2e-raw.json`, a different
   algorithm doing a similar job — a finisher with the slice baked in at a
   fixed width. The card's cue "slice out, run it, slice back -- both cubes"
   was therefore false of the string printed beside it. It now reads the
   verified flip, and the cue is true for the first time.

**A stated invariant broke, deliberately.** `notation.py` asserted that no
big-cube chunk block is compacted *because* every big-cube string carries a
layer-count prefix. The flip is the first that does not — which is exactly the
property that makes it identical on both cubes. The table stays uncompacted by
choice now, and the comment says so rather than claiming a property of the data.

`test_cube.py` gained the matching exception: every big-cube string must bounce
off the 3×3 simulator, except the flip, which must be legal. A new outer-turn
string appearing in that table fails the test until someone decides.

**No 5×5 SVG path was built, and none is needed.** With twelve cases locked the
remaining pictures are the centre insert, the flip and the parity case — all
player material. The KNOWN LIMIT in `gen-case-states.mjs` and its Python pin
stay exactly as they were: both remain true, and they still guard the twelve.

## The not-reached grey is warm, not blue (2026-08-28)

Reported: "the grey looks blue". It did, and it was: `UNREACHED = #C0D4E6`,
b\* −11.1 — a pale cool tint on every step and F2L diagram, which is 60 of the
221 shipped SVGs and the largest single region in most of them.

**Why it was blue.** The tier has to be distinguishable from the white face
*and* recede into the page, and those two are 1.6 ΔE apart (`#FFFFFF` vs
`--paper #FCFBF8`). A light neutral cannot clear both, so the tone has to buy
its distance with a tint. Blue bought 19.7 ΔE off white for almost nothing.

**Why that was the wrong purchase.** The cube already owns a blue face, and the
five dim tones the tier shares every picture with are warm or muted (`#BEAB7A`
tan, `#CA8876` salmon, `#9ABCA6` sage, `#A07757`, `#797C9F`). A pale blue among
them does not read as "the method has not reached here" — it reads as a seventh
sticker colour. On `f2l/f2l_01.svg` the not-reached region is two whole faces,
so the picture read as a light-blue cube with a few real stickers on it.

**The new value:** `#D8D5CF`, b\* +3.3, L\* 85.3 — a warm grey one step lighter
than the OLL mask and recognisably the same KIND of grey, which is the point:
both are "grey" to a reader and only the tone carries the different claim.

Getting there took two passes, and the first is worth recording. Warming the
tier gives up the cheap separation blue was buying, so the first attempt paid
for it in lightness instead — `#E6E3DD`, L\* 90.3 — and read as a hole in the
page rather than as a grey. The brightness was not a taste error; it was forced
by the ≥12 ΔE two-greys gate, because a neutral can only buy distance from a
neutral mask with lightness, and every point of that gate pushed the tier
further toward the page and toward the white face it also has to clear.

**So the SCREEN gate moved, deliberately, from 12 to 8.** It was doing a job it does
not need to do. The split is enforced absolutely by a different assertion —
`test_no_diagram_ever_carries_both_greys` — and the two tones only ever appear
NEAR each other, on a page where `yellow-cross.mdx` prints `step_4_ycross`
above the three OLL cross cases. 8.3 ΔE is ~3.5 JND plus a neutral-vs-warm hue
change, which is ample at that distance. Lowering it let the tier come down to
L\* 85, where the real floor is: DIM WHITE (`#ABABAB`), the one neighbour with
no hue to separate it, at 15.7 ΔE against a ≥15 gate.

The trade against the old blue: white-vs-not-reached goes 19.7 → 15.0 ΔE (the
warm pass at `#E6E3DD` would have made it 10.2), and mask-vs-not-reached goes
13.1 → 8.3. A hue collision no stroke can fix was traded for a lightness gap
every stroke already handles.

**White-vs-not-reached is now gated, because it is the number that moved.** The
dim gate covers `dim(WHITE)`; nothing covered the FULL white face, which sits
polygon-to-polygon with the tier in `step_1_cross` and every F2L picture. It is
the tier's only binding neighbour — 15.0 ΔE where every other face is 60+ — and
the whole "no lighter than this" argument above is an argument about it, so
`test_a_full_face_is_separable_from_the_not_reached_tone_too` measures it at a
≥15 floor. The tone sits ON that floor: brighten it and this fails first.

Every other gate held unchanged: the lighter-than-the-mask relation, the dim
separation on both palettes, the never-both-greys-in-one-file rule, and the
14-way `_restyle` collision check.
The card palette is untouched — `CARD.unreached` stays `#3F3F3F`, because print
inverts the tier for reasons of medium, not hue — and **so is the card's
two-greys floor, which stays at 12** (it sits at 13.7). None of the argument
above is about the card: it prints on a mono laser where hue is gone and only
the luminance gap survives, so relaxing its floor alongside the screen's would
have given away a gate for nothing.

**Not changed: the 3D player.** The obvious follow-on is to make cubing.js's
tones match the SVG palette. It was tried and rejected on evidence. The 3×3
renderer keeps its colours in six shared `AxisInfo` materials, which can be
repainted through `experimentalCurrentThreeJSPuzzleObject()` and survive
animation. PG3D — the 4×4/5×5 renderer — keeps them as **vertex colours** in a
shared buffer that `StickerDef.setColor` re-copies from `origColorStickeringMask`
on every animated frame, so a repaint holds until the first move and then
reverts sticker by sticker (verified in a headless browser). Repainting only
the 3×3 would leave the site with two player palettes where it currently has
one, which is less united, not more. So the players stay stock and the seam
stays where CLAUDE.md already puts it: the shared artifact between the two
renderers is stages.json's tier ASSIGNMENT, never the colours.

## The reference gaps, the big-cube cut, and a glossary (Aug 2026)

Six complaints, all from one look at `/reference`, plus two follow-ups. What
follows is what each turned out to be, because in every case the visible symptom
was downstream of a data or pipeline decision rather than of the page.

**The 5×5 case showed a tile reading "6", with no picture and no algorithm.**
Two separate causes. The section was a TILE GRID, which is right for 57 OLL
cases and wrong for a set with one visible member — a lone tile carries a
diagram and nothing else, so the algorithm and the recognition cue had nowhere
to go. It is a `rows` section now, like the 4×4 parity section beside it. And
the case genuinely had no diagram: `gen-case-states.mjs` carried a KNOWN LIMIT
saying the 13 L2E states were "exported RAW and not yet drawable", because an
L2E algorithm is written for a hold partway through reduction, so `alg⁻¹` is not
a picture of the case — it leaves the target groups wherever that hold put them
and rigidly cycles others. That comment also named the fix, and the fix is what
was done: `verify-l2e.mjs` already BUILT the displayed pattern in its check (d)
and round-tripped it, so it now exports it as `displayed` (a delta against
solved), `gen-case-states.mjs` patches it onto the default pattern under a third
`derivation`, and Python draws it. The result is the canonical parity picture —
two wings showing the side colour on top, the midge right.

A REAL BUG fell out of that. `verify-l2e.mjs` built its synthetic pattern with
`structuredClone(solved.patternData)`, and cubing.js hands every orbit of the
same length the SAME zero-filled orientation array — on a 5×5, EDGES, CENTERS
and CENTERS2 are all 24 slots and all three are literally one array, which a
clone faithfully preserves. So `synth.EDGES.orientation[i] = …` also wrote both
centre orbits. It changed no check (centres are compared by piece, and CENTERS
has numOrientations 1) and would have changed no picture; it became visible only
when the pattern was exported, at which point every case claimed centre twists
it does not have. `unaliasedCopy` fixes it and a self-check proves both halves —
that cubing.js still aliases, and that the helper breaks it.

**"Why do we not call the 4×4 PLL parity?"** Because the name came from JPerm's
set, where the case is "Pure-E". Its algorithm IS the bare PLL-parity string
byte for byte, so the case is renamed "PLL Parity (4×4)" through a deliberately
tiny `NAME_OVERRIDES` map in `gen-cases.mjs` — two entries, both parity, both
cross-checked in `tests/algs.spec.ts` against `case-states.json`'s own
`parityAlgs`. Cases whose only identity is an index ("L2E 11", "OLL 33") keep
the index; inventing names for cases nobody names is worse.

**"Is the image correct with the arrows?"** Yes — verified against the kpuzzle
state, facelet by facelet. The picture shows a diagonal corner swap plus a
left–right edge-pair swap, which reads as more than parity, and that is honest
rather than wrong: the algorithm `2R2 U2 2R2 Uw2 2R2 Uw2` contains `U2 Uw2 Uw2`,
so it leaves the corners a U2 from home, and the case state is the state that
algorithm solves. Nothing was changed in the diagram; the recognition cue was
rewritten to say so in words.

**4×4 OLL parity had no picture at all**, and could not have had one from the
existing pipeline: every case in JPerm's 27-case 4×4 OLL set has the parity
algorithm SPLICED INTO a last-layer algorithm, so not one of them is bare
parity. It is built now, and NOT as `alg⁻¹` — that would draw a last layer with
twisted corners in it, a state no solver meets and one the case's own
recognition line contradicts. Parity is not a case an algorithm solves; it is a
class the algorithm moves you out of. So the RECOGNITION state is constructed —
the odd wing exchange that IS parity — with the orientation chosen by the
picture (of the two candidates, exactly one reads as a flipped pair, asserted)
and the result gated on wing PARITY: the built state must be odd, and the state
after the algorithm must be even with every edge group intact. Deliberately not
asserted: that the algorithm solves the cube, or even leaves the U face one
colour. Measured, it leaves two edge pairs swapped and two corners twisted.

**The beginner algorithms were nowhere.** `R U R' U'` is printed in three
lessons, `L' U' L U` in two, Niklas in one, and the big-cube edge flip in two —
and not one of them had a case, so none had a /reference row, a /case page, a 3D
player, or anything verifying it. `gen-case-states.mjs` said so in as many
words about the flip: "the one algorithm the big-cube course teaches that has no
case of its own". They are cases now. The interesting part is the gate: a
trigger has no recognition state, so none of the four stickering invariants
applies, and rather than widen an invariant until it accepted them each is
pinned by BEHAVIOUR — and the behaviour pinned is the claim its own lesson
makes, so "six righty triggers in a row return the cube exactly to where it
started" now fails the build if it stops being true.

**The big-cube case sets are no longer drawn.** The course teaches reduction
(Yau as the advanced variant), so a 4×4 or 5×5 becomes a 3×3 and the 3×3 sets
finish it; the 27 4×4 OLL, 22 4×4 PLL and 13 5×5 L2E cases are one-look
optimisations already locked out of every surface by `unlocks.ts`. Their 61 SVGs
were therefore reachable from no page, which makes them the worst kind of
artifact — committed, and unverifiable by looking. Deleted, and the trees are
the gate. Their DATA stays: the parity algorithms are located inside those sets
BY MECHANISM ("the one string that appears verbatim inside dozens of others"),
so deleting the sets would break how the repo derives the algorithms it does
teach. `big_oll_cases()` / `big_pll_cases()` also stay as unrendered builders,
because they are what the 4×4 half of the plan-view renderer is checked
against and the two shipped 4×4 diagrams come out of the same code.

One consequence, stated because it weakens a property CLAUDE.md advertises:
unlocking a set no longer restores every surface from one boolean. The cases
come back with no icons, through /reference's existing "no diagrams for this set
yet" fallback, until a group is added back to `render_big_sets`.

**The course index showed a 3×3 with a letter on it for 4×4 and for 5×5.** The
two big-cube phase cards pointed at NOTATION diagrams — `move_rw.svg` and
`move_m.svg` — which are 3×3 cubes with a large black "r (Rw)" or "M" across
them, and at 155px of art squeezed into a 96px box, so the cube inside came out
smaller than every other card's. The isometric renderer takes a cube order now:
the projection stays in a three-unit box and only the cell size changes, so a
4×4 and a 5×5 sit at exactly the same size as a 3×3 beside them. Both cards show
a real big cube mid-reduction — centres built, edges not yet paired — which is
the phase's actual content, and a finished big cube would have been
indistinguishable from a finished 3×3. Two more cards were wrong at that size
and are fixed with them: Basics pointed at `step_flip`, three-quarters grey
because it is drawn for the moment before the first layer exists; Phase 3
pointed at the beginner ladder's step 6, indistinguishable from step 5 on the
card above it.

**A glossary, hoverable in place.** `src/data/glossary.ts` is the vocabulary;
`scripts/rehype-glossary.mjs` rewrites the first mention of each term in each
lesson into a link to its entry with the definition on it. A `<Term>` component
was rejected: 25 files to edit, a judgement call at every occurrence, and markup
that rots when a term is renamed. Two mechanical facts are worth writing down
because both cost a debugging pass. `mdx({ rehypePlugins })` is deprecated and
on this version SILENTLY DOES NOTHING — one build warning, then 25 pages with no
links; `markdown.processor: unified({ rehypePlugins })` is the current API and
MDX inherits it. And the hover card must be `display: none`, not
`visibility: hidden`: a hidden absolutely-positioned box still contributes to
scrollable overflow, and every lesson page scrolled 50px sideways at 375px until
it was taken out of layout — caught by `e2e/regressions.spec.ts` on all 25 at
once, which is exactly the test earning its keep.

**The 5×5 parity player used to disagree with its diagram — fixed by the MASK,
not by the state.** `/case/555.l2e-6/`'s player starts from `solved · alg⁻¹`,
and running an L2E algorithm backwards turns its SIDE EFFECTS into apparent
parts of the case: measured, the UL and UR groups and two corners, exactly the
two swaps the lesson names a paragraph away. So the player lit three edge groups
where the diagram showed one.

The first instinct was to fix the STATE — derive a setup sequence so the player
starts where the diagram is drawn. That is a solver problem (the hold is a
parity state, unreachable by the algorithm itself) and it was not needed. The
mask is the layer that decides what a picture is ABOUT, and it was deriving its
highlight from `solved · alg⁻¹` like every other case. Pointing it at the
exported hold instead lights the flipped pair and dims everything else, so the
player and the SVG now emphasise the same thing. The two side-effect groups are
still physically displaced in the player — they have to be, the algorithm has to
undo them — but they read as DIM, which is the honest tier: at the pairing stage
a group that is intact but displaced is finished, and the 3×3 stage places it.

Worth stating as a general lesson: when a picture emphasises the wrong thing,
the mask is usually the layer to fix, not the state.

**Naming, after the fact: "L2E" named a set the course does not teach.** The
group key, the trainer set and the reference section were all called `555-l2e`,
inherited from the data source — `l2e-raw.json` is SpeedCubeDB's L2E set — and
twelve of those thirteen cases are locked, so the name pointed at content that
is not there. Three different things had been given one name, and they are
separated now:

- the STEP of the solve is "the last two edges", which is universal in reduction
  and is what the lesson is about — its title is now "5×5: Last Two Edges and
  Parity", matching the sibling "4×4: The 3×3 Stage and Parity";
- the SOURCE SET of thirteen is L2E, and keeps that name everywhere it is the
  subject: `l2e-raw.json`, `verify-l2e.mjs`, the case ids `555.l2e-N`, and the
  unlock key `555-l2e-onelook`, which names precisely the set it hides;
- what the COURSE TEACHES is 5×5 edge parity, so the group key is `555-parity`
  (symmetric with `444-parity`), and so are the trainer set, the reference
  section and the case.

The abbreviation itself is gone from reader-facing prose. The card set already
bans that class of shorthand — `glossary.py`'s `BANNED` maps "dedge" to "edge
pair" for the same reason — and "L2E" was appearing unexpanded twice in a lesson
body. Data and verifier filenames keep it, because there it is provenance.

## Checked against J Perm's own tutorials (Aug 2026)

The transcripts of J Perm's 4×4 and 5×5 beginner videos are in
`docs/other_guides/jperm/` (git-ignored — not ours to redistribute). Three
questions were checked against them directly rather than from memory.

**Does Cubepath teach the 4×4 in his order?** No, and deliberately. His 4×4
video is a **Yau** tutorial from the first minute: white centre, yellow centre,
three cross dedges, last four centres, remaining dedges, 3×3, OLL parity, PLL
parity. Cubepath teaches plain reduction (all centres, all dedges, 3×3, parity)
and offers Yau as the upgrade in `444-yau-intro`, whose opening callout already
says so in as many words. Plain reduction is the easier ladder — Yau's last-four-
centres step has to preserve a partial cross, which is a constraint a first-time
solver has no reason to carry — and his own 5×5 *beginner* video teaches plain
reduction, so he is not consistent across the two either. Everything else lines
up: bars for centres, storing with an unpaired dedge as the replacement, the
2-then-3-2-3 rhythm, the flip for the last two, OLL parity before PLL parity.
One gotcha of his is deliberately absent — the colour-ring check ("after blue
goes orange") — because it only bites in Yau, where the side centres do not
exist yet when you place a cross dedge. Under reduction the centres are already
built, so you match colours to them.

**Can the centre insert have a reference entry when it is not an algorithm?**
It was given one — `444.center-insert` / `555.center-insert`, showing the shape
plus several worked instances — and then REVERTED, on the user's call: *"this
center insert should be intuitive and not get a separate reference."* That is
the right call and the reasoning is worth keeping. Printing one instance as "the
centre algorithm" is the mistake the technique is defined against; showing three
instead fixes the accuracy but not the premise, because the thing still is not
lookup material. Centres are aimed, not recalled, and the lessons already teach
them with a worked figure and an explicit "there is no algorithm on this page".
A reference row would have been a well-built answer to a question nobody asked.

Randomising the shown instance ("a different example each visit") was rejected
before that, and separately: it makes a page unreproducible, unscreenshotable
and untestable, and the randomness belongs in the trainer if anywhere.

What the request actually meant was the centre SWAP — moving one of the nine
centre pieces from one centre to another, the trick J Perm walks through at 3:08
of the 5×5 video. A first attempt at answering it offered
`2R U 2R' U 2R U2 2R'` (Sune with the inner slice), which does swap exactly one
centre piece between two centres on both cubes — but it is not the thing in the
video, and it was rejected on that ground.

Searching the kpuzzle settled what the video's pattern can and cannot be. Over
every alternating slice/U sequence up to five moves, **nothing shorter than
three moves moves a piece between two centres while leaving the other four
whole**, and at three moves every solution is the same conjugate with a
different grab — `Rw U Rw'`, `2R U 2R'`, `M' U M`, `2L' U 2L`. So the insert
already in the lesson IS the tool, and the only choice is the grab.

Which explains why J Perm's version is longer and why he refuses to name it:
his is the same insert **twice, in two different layers**. Its purpose is to
preserve PARTIAL progress on the target face — the last bar, where the only
thing left to displace is what you just built — and that is a property of a
half-built centre, so it cannot be measured against a solved cube at all. That
is the real reason it is a pattern and not an algorithm, and it is now written
into `555-centers-edges.mdx` in his beats. No reference entry, per the same
call as the insert: centres are aimed, not looked up.

**Jargon is allowed now.** The site wrote plain phrases and glossed them inline;
with a hover card on every first mention, `dedge` is the headword and `edge
pair` the alias. The printed cards keep the ban (`glossary.py`'s `BANNED`),
because paper has no hover — that split is the point, not an oversight.
