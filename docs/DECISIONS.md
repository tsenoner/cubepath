# Decision log — autonomous build

Decisions made during the autonomous PWA build (Aug 2026), beyond what the
master plan (docs/master-plan.html) and the user's locked answers specify.
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
  counterparts defined in design/build_canvas.py.
- **Signature elements**: trigger-colored monospace algorithms, real derived
  case diagrams inline, guide callout system on the web, case-row anatomy
  (diagram / name+recognition / alg / status / play).
- design/ holds the generator (build_canvas.py) + artboards; re-run and
  re-seed to update the canvas.

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
  file-payload path and `scripts/build-deploy-payload.py` are retained only
  as a manual fallback. Production alias: https://cubepath-six.vercel.app.
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

## Card SET — planned, not built

`docs/card-set-plan.md` is the research-backed build order for a staged card
set (3 numbered cards + 1 annex). Two load-bearing conclusions:

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
- `docs/card-set-plan.md` §3 predicted `F 33.8` / `Na 39.3`; those numbers
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
