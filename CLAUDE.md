# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands

The root `Makefile` is the single source of truth for the repo's command
surface. The pre-push hook and CI call its targets instead of re-listing
commands, so the two gates cannot drift apart. Run `make` for the full list.

```bash
make install   # install app + Python dependencies
make dev       # app dev server -> http://localhost:4321
make check     # local gate: check-py + check-app (what the pre-push hook runs)
make fmt       # apply every formatter/autofix: prettier, eslint --fix, ruff
make ci        # check + Playwright E2E (what GitHub Actions runs)
make build     # diagrams + PDF guide + card set + app
make diagrams  # regenerate SVG diagrams + sync into the app
```

Two gates, deliberately different: `make check` is fast and runs on every push;
`make ci` adds the Playwright E2E suite and runs in CI. Changing a command means
editing the Makefile — never re-list commands in the hook or the workflow.

Both halves of the repo are linted, formatted and type-checked, and every one
of those is part of `make check`:

| | Python (`tools/cubepath`) | App (`app/`) |
| --- | --- | --- |
| lint | `ruff check` | `eslint .` (typescript-eslint + eslint-plugin-astro) |
| format | `ruff format --check` | `prettier --check .` |
| types | `mypy` (strict on `src/`, relaxed on `tests/`) | `astro check` (`strictest`) + `tsc -p scripts/tsconfig.json` |
| tests | `pytest` | `vitest`, the data verifiers, `astro build` |

`make fmt` is the write side of the same list. Prettier and ruff both wrap at
100 columns, so the two halves of the repo look alike.

Individual tools still run directly when working inside one subtree:

```bash
cd tools/cubepath
uv run cubepath-diagrams   # generate SVG diagrams
uv run cubepath-cards      # generate the printable card set + print sheets
uv run pytest tests/       # run tests
uv run pytest tests/test_diagrams.py::test_all_cases_count   # single test
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy                # strict type gate (paths come from pyproject.toml)
```

**Prerequisites:** uv, pandoc (>=3.1.2, for the typst writer), typst,
poppler (`pdfinfo` + `pdftotext` — the card build gates shell out to them),
Node >= 22.12 (app/)

**Local CI gate:** run `git config core.hooksPath .githooks` once per clone.
The pre-push hook runs `make check` — a push that would fail CI is rejected
locally.

## Repo layout

| path | what lives there |
| --- | --- |
| `app/` | the Astro PWA — 25 MDX lessons, the trainer, the reference set |
| `tools/cubepath/` | build-time Python: simulator, diagrams, card set, logo |
| `guide/` | `cubepath.md` + the pandoc/typst build for the PDF companion |
| `docs/` | live reference; `docs/archive/` is finished work kept for provenance |
| `scripts/` | multi-step build logic too long to inline in the Makefile |

`docs/README.md` is the index: `DECISIONS.md` (append-only, always current),
`printing.md`, `resources.md`, `TODO.md` (open items only — completed ones move
into `DECISIONS.md`) and `research/tech-brief.md`, which stays live because two
app scripts pin their big-cube algorithm strings to its §8. Everything under
`docs/archive/` carries a banner naming what superseded it; nothing there
describes the project as it is.

## Generated artifacts committed under `app/`

Vercel builds only `cd app && npm ci && npm run build` — no Python, pandoc,
typst or poppler on the runner — so anything the app serves has to be committed,
generated locally. That makes silent staleness the failure mode, and every one
of these is therefore pinned by a test:

| artifact | produced by | pinned by |
| --- | --- | --- |
| `app/public/cubepath.pdf` | `make build-guide` | `tests/test_guide.py` (input digest in `guide/pdf.stamp.json`) |
| `app/public/diagrams/**` (131 SVGs) | `make diagrams` | `tests/test_diagrams.py` — generator match + byte-identity with `guide/figures/generated/` |
| `app/public/cards/*.pdf`, `app/src/data/cards.json` | `make cards` | `tests/test_cards.py` |
| `app/public/favicon.svg`, `app/public/icons/*.png` | `make logo` | `tests/test_logo.py` |
| `app/src/data/fullsets*.gen.ts` | `node scripts/gen-cases.mjs` | `app/tests/algs.spec.ts` (kpuzzle) |

A PDF cannot be compared to its markdown — typst output is not byte-
reproducible — so `make build-guide` stamps the **inputs** instead
(`scripts/guide_stamp.py`: the markdown, the pandoc/typst config, the Lua
filter, and only the 51 figures `cubepath.md` actually references) and the test
recomputes that digest. Edit the guide and forget to rebuild, and `make check`
fails. This gate exists because the shipped PDF went two content revisions
stale in production without anything noticing.

`make build-guide` depends on `make diagrams`, so the guide can never be built
against a diagram tree the app has not been given. Never run `pandoc` or
`cubepath-diagrams` by hand and commit the result — go through the Makefile, or
the stamp and the byte-identity gate will disagree with the tree.

## App (app/)

Astro + TypeScript strict PWA (offline-first). Commands, from `app/`:

```bash
npm run dev / build / preview
npm run lint             # eslint (add :fix to autofix)
npm run format:check     # prettier (npm run format to write)
npx astro check          # strictest type gate for src/ + e2e/ + tests/
npm run check:scripts    # tsc --checkJs over scripts/*.mjs
npx vitest run           # every algorithm machine-verified on the cubing.js kpuzzle
npx playwright test      # smoke + airplane-mode E2E (the PWA gate) + axe a11y
node scripts/gen-cases.mjs      # regenerate src/data/fullsets.gen.ts + .rich.gen.ts
node scripts/extract-algs.mjs   # re-extract + verify the JPerm dataset (gated write)
node scripts/verify-f2l.mjs     # F2L-41 verifier
node scripts/verify-l2e.mjs     # 5x5 L2E verifier (gated write of l2e-raw.json)
node scripts/gen-icons.mjs      # rasterize the PWA icon set from favicon.svg
node scripts/gen-stickering.mjs # regenerate the twisty-player stickering masks
```

**Everything under `app/scripts/` is type-checked** (`scripts/tsconfig.json`,
`checkJs: true`) — it generates the shipped algorithm data and runs the F2L/L2E
verifiers, so a type error there can silently weaken the verification it exists
to perform. Annotate new scripts with JSDoc; do not add a script that opts out.
The scripts stay on `strict` rather than the app's `strictest`, because
`noUncheckedIndexedAccess` costs ~99 casts in dense cube-math indexing that JS
cannot write as `!`.

Two Prettier settings are load-bearing, not taste: `.prettierignore` excludes
`src/content` (its MDX printer rewrites `*italic*` and explodes the lesson
figures) and the generated data files, and `quoteProps: "preserve"` keeps the
quoted keys `gen-stickering.mjs` writes into `src/lib/stickering.ts` — without
it, formatting and regenerating that file fight each other forever.

Brand mark: an isometric cube with a yellow route climbing the front face and
crossing the top. `cubepath.logo` (Python) is the source of truth — its 23 paths
are bezier strings no one can retune by hand, so the trail shape, face tones,
radii and sticker gap are constants there. `make logo` regenerates
`app/public/favicon.svg` and rasterizes every PNG from it via `gen-icons.mjs`;
never hand-edit the SVG or the icons, because `test_logo.py` fails the gate when
the committed favicon stops matching the generator. Face tones are mirrored in
`tokens.css` as `--logo-*` (light + dark), which `Header.astro` binds the same
paths to; the favicon carries its own `prefers-color-scheme` block because it
loads outside the page and cannot see the tokens.

The route is drawn as flush yellow stickers, chosen for punch. It is **not a
reachable cube position**, and that is a deliberate call rather than an oversight:
a contiguous sticker path can never legally cross a cube edge, because the two
facelets either side of an edge always belong to the same piece. Here the UF edge
would need yellow on both its U and F facelets, and the U and F centres would both
be yellow. The mark is a graphic, not a derived position — the one place in this
repo that does not follow the derive-everything rule.

Data flow: `src/data/extracted/*.json` (verified extractions) + `src/data/recognition.json`
(hand-written cues) → `gen-cases.mjs` →
`fullsets.gen.ts` (lean, ships to client) + `fullsets.rich.gen.ts` (recognition +
alternates, build-time only) → merged with curated entries in `src/data/algs.ts`
(`ALL_CASES`). Never hand-edit generated files; never retype algorithms — every
alg is kpuzzle-verified in `tests/algs.spec.ts`.

Deploys: Vercel project `cubepath` (deploy setup in docs/DECISIONS.md § Deploys), git-linked via
the Vercel GitHub App — **every push to master auto-deploys** to
https://cubepath-six.vercel.app (root `vercel.json` builds from `app/`).
Manual fallback only: `vercel login && cd app && vercel deploy --prod`, or the
Vercel MCP.

**There is exactly one `vercel.json`, at the repo root.** Vercel reads the
config at the project's Root Directory, which is the repo root here — a second
copy under `app/` is never parsed, so an edit to it (the `/sw.js` no-cache
header is the PWA's whole update mechanism) would look correct, pass review and
do nothing. One existed and was deleted; do not recreate it. JSON has no comment
syntax and Vercel rejects unknown root keys, which is why this note lives here
rather than in the file.

## Build-time Python tooling (tools/cubepath/)

One `uv` project, package `cubepath`, four entry points: the SVG diagram
generator, the card set, the logo, and the cube simulator they all derive from.
The directory was `tools/diagrams/` until cards and the logo landed in it; it is
named for the package now (`parents[N]` depths are unchanged, so no code moved).

### Cube Simulator

`tools/cubepath/src/cubepath/cube.py` is a minimal Rubik's cube simulator (~330 lines). Used at build time by `diagrams.py`, `fullsets.py` and `recognition.py` to derive sticker states and card recognition cues, and by tests to verify diagram sticker colors and algorithm correctness. State: 6 faces × 9 stickers (row-major). Table-driven moves (R/L/U/D/F/B/M/S/E + wide/rotations). Algorithm parser handles `R U R' U'`, `R2`, lowercase wide (`r`, `f`), and `(R U)×2` repeats. Coordinate mapping `diagram_to_sim(face, a, b)` bridges diagram coords to simulator state.

### Algorithm Data

`tools/cubepath/src/cubepath/algs.py` is the single source of truth for the 22 algorithms the guide teaches. The full 57-OLL / 21-PLL sets are derived from the app's verified extraction via `fullsets.py`; 15 of the 21 PLLs (all but `notation.PLL_OWNED`) and the four big-cube strings come from there too. Diagrams derive their sticker states from these strings via the simulator; `tests/test_derivation.py` asserts the guide's tables match, arrows match the real piece permutation, and the 7 corner-orientation algs cover all 7 OCLL classes. Never hand-define sticker layouts — derive them.

### Diagram Pipeline

`tools/cubepath/src/cubepath/diagrams.py` defines the guide's 17 core cube diagrams as `CubeDiagram` dataclasses rendered to SVG using `svgwrite`. Case sticker data is **derived from algorithms** via `_derived_cross_case` / `_derived_oll_corner_case` / `_derived_pll_case` (OLL: yellow/grey masks; PLL: true colors). The entry point `cubepath-diagrams` writes to `guide/figures/generated/`.

Four case groups: `_oll_cross_cases()` (3), `_oll_corner_cases()` (8), `_pll_corner_cases()` (2), `_pll_edge_cases()` (4). `fullsets.py` builds a further 78 (57 OLL + 21 PLL) from the app's extraction, into `oll-full/` and `pll-full/`.

OLL cases have no arrows; PLL cases use `swaps` (bidirectional), `cycles` (directional) and
`dashed_swaps` (the secondary edge movement in a corner PLL) arrow fields — hand-declared for layout but permutation-verified by tests.

`render_overview` draws the notation overview — the six face turns on one cube — in one
of two layouts. `OVERVIEW_PINS` is the shipped `overview.svg`: a pin out of every face
centre, a dot at its tip, the letter beyond it, and a 3D ribbon ring around each pin
showing which way that face turns, clockwise as seen from outside it; the hidden faces'
pins and rings run behind the cube, which occludes their inner half, and their dots go
under their rings (the tip is beyond the ring's plane, away from the camera) where the
visible faces' dots go over. The ribbon is the
original figure's geometry (`_ribbon_arc`: a band around the axis split into back and
front halves around the pin, arrowhead in the band's own plane) at a radius and sweep that
survive 272 px; pin lengths are solved from two screen radii (`_OV_PIN_TIP`) and the
arrowhead's position on the ring is derived from the view direction, never hand-set.
`OVERVIEW_HUB` (`overview_hub.svg`, kept as the backup) shows the turns as the reader
sees them: F spins as a ring in the middle of the front face and every other letter slides
its layer along an edge of a visible face, with the strip directions **derived** —
`_strip_arrow` marks the strip on a solved cube, applies the letter, and points at the
face the marks left for (`exit_face`). Both are gated: rings must pass their face's
edge-middle stickers in the order one turn carries a sticker, the layer table
`_LAYER_OF` is checked against the simulator, every arrowhead in the SVG is the projected
end of an arrow, and the computed frame holds every coordinate and label. Slices,
rotations and modifiers stay in the fifteen move diagrams: they did not fit on the same
cube without a second idiom, and a nine-arrow version was judged less clear than the pins.
The same function renders the annex card's copy (the pins) in `CARD` style; when
`_ov_needs_halo` finds the palette fails 3:1 against the ink, the pins' on-face segments
and the hub's arrows get a paper-coloured halo (the ribbons carry their own paper fill).
On screen the figure flips with the theme through three classes in `_THEME_CSS`: `.ink`
(filled labels and dots), `.ink-stroke` (a pin's run across the plate) and `.paper` (the
ribbons' occluding fill: white by default, `DARK_PAPER` in the dark scheme — pinned to
`tokens.css` by a test, because an occluder only works if it is the page); a pin is split
where it leaves its face, because its on-face run has to stay dark against the sticker
colour.

`StepDiagram` dataclasses produce 3D isometric progress/case diagrams: `_step_cases()` (8 steps), `_corner_case_steps()` (3), `_edge_case_steps()` (2), `_orient_corner_case()` (1), `_orient_corner_cases_15()` (2), `_corner_pos_case()` (1), `_align_edge_cases()` (2) — 19 in all, composed by the public
`all_steps()`, which both the guide build and the card generator render, so a new step group
must be surfaced there or it reaches neither output. Each specifies a solved-sticker set, optional face_colors override (e.g. flipped white-on-top), and sticker overrides for highlighting.

### Guide Build

`guide/cubepath.md` is the single source file. Pandoc builds PDF using `guide/defaults/pdf.yaml` (Typst output), passing through `guide/filters/callouts.lua`.

### Card set (`cubepath-cards`)

**Four ID-1 panels** (85.6 × 53.98 mm): three numbered progression cards plus an annex.
`make cards` builds them into `guide/build/cards/` and copies the **PDFs** to
`app/public/cards/`; the same run writes the manifest payload (`{cards, sheets}`) to
`guide/build/cards/manifest.json` and to `app/src/data/cards.json`, which is the copy the
app imports and the one `tests/test_cards.py` pins to the generator (CI never runs
`cubepath-cards`, so nothing else would catch drift);
the app serves them from `/print` and from the frozen routes `/c0`–`/c3`.

| module | owns |
| --- | --- |
| `cards.py` | what each card *says* — the deck table and the four cards' content |
| `cheatcards.py` | imposition, build gates, CLI, `manifest.json` |
| `recognition.py` | PLL cues and Sune counts, **derived** from the cube state |
| `glossary.py` | `GLOSS` / `TEACH` / `DEMONSTRATED` / `BANNED` / `PLAIN` tiers; `BANNED` + `PLAIN` are gated on every rendered card |
| `typst.py` | algorithm → Typst markup, shared by `cards.py` and `cheatcards.py` |

Nothing on a card is retyped. 3×3 algorithms come from `algs.py` via
`notation.CHUNKS`, PLL via `notation.PLL_CHUNKS`; the four big-cube strings are read
out of the app scripts that pin them for CI (`extract-algs.mjs`, `verify-l2e.mjs`,
`l2e-raw.json`). Trigger colours are derived by exact-token lookup in `palette.FAMILY`,
and recognition wording is generated from the same permutation the diagram is drawn
from — a wrong cue is a template bug, never a mis-copied case.

Diagrams are **re-rendered** in `diagrams.CARD` style, never post-processed: the card
palette is chosen against `palette.contrast` and gated, because at card size on a mono
printer hue is gone and only luminance survives.

Failure modes the generator gates on every build, because each silently ships a wrong
card. The five below are the subtle ones; `gate_card` also checks page geometry, banned
and never-introduce vocabulary, and raw-markup leaks (the leak patterns are *derived*
from the preamble's `#let` helpers, so a helper added later is covered by construction):

1. Typst rewrites ASCII primes to U+2019, which cubing.js refuses to parse.
2. Typst exits 0 on an unknown font family (so `--ignore-system-fonts`, warnings fatal).
3. Typst paginates silently on overflow — the page count is asserted.
4. A fixed-height card does **not** paginate when it overruns; it overlaps its own
   footer. `fit()` measures the real rendered height in Typst and refuses to compile.
5. A duplex imposition that pairs the wrong front with the wrong back looks perfect on
   a proof sheet. The row-duplication theorem is asserted, not assumed.

`/c0`–`/c3` are **printed on card stock and can never change or 404** — Playwright
treats them as a public contract. See `docs/printing.md` for print/duplex/lamination
guidance and `docs/archive/card-set-plan.md` for why the set stops at three
cards.

### Lua Filter (`guide/filters/callouts.lua`)

Handles five things:

1. **Callout divs** — Fenced divs with classes `.algorithm`, `.tip`, `.caution`, `.info` become styled Typst `#block()` markup. A `title=` attribute overrides the default label.

2. **Steps div** — `:::: {.steps}` wraps the Phase 1 step tables in a mirrored 4-column Typst grid layout.

3. **Image rotation** — `![alt](path){ rotate=180 }` attribute wraps in `#box(width, rotate(..., image(...)))`. This keeps rotated images inline (important for side-by-side figure rows). Meaningful for plan-view (top-down) diagrams, where the turn picks a different AUF — **not** for 3D isometric ones, which it just prints upside down.

4. **Trigger-colour spans** — `[R U R' U']{.trig-r}` (also `.trig-g`, `.trig-b`) becomes bold coloured Typst text. The hexes are kept in sync with `cubepath/palette.py` and `tests/test_notation.py` fails the build if they drift.

5. **Borderless tables** — `::: {.borderless}` converts a table to a Typst `#grid()` so columns distribute equally.

## Rubik's Cube Color Scheme & Physics

Standard Western color scheme with **Yellow on top, White on bottom, Red in front**:

| Face | Direction | Color | Opposite |
|------|-----------|-------|----------|
| U (Up) | +y (top) | Yellow | White (D) |
| D (Down) | -y (bottom) | White | Yellow (U) |
| F (Front) | +z (toward viewer) | Red | Orange (B) |
| B (Back) | -z (away) | Orange | Red (F) |
| R (Right) | +x (right) | **Green** | Blue (L) |
| L (Left) | -x (left) | **Blue** | Green (R) |

**Adjacency (CW from top):** Orange → Green → Red → Blue → Orange. So with Red in front: R=Green, L=Blue.

**3D isometric view** shows three faces: U (Yellow, top), F (Red, front-left), R (Green, front-right).

**Move rotation direction:** CW when looking at the face from outside. For the isometric projection:
- R CW from +x: top→back→bottom→front (F→U→B→D→F). In yz plane: (y, z) → (z, 2−y).
- U CW from +y: front→left→back→right (F→L→B→R→F). In xz plane: similar.
- F CW from +z: top→right→bottom→left (U→R→D→L→U). In xy plane: similar.
- L/D follow opposite-face conventions. M follows L direction, S follows F direction, E follows D direction.

**This section is machine-checked.** `tests/test_conventions.py` parses the table,
the adjacency ring, the `(F→U→B→D→F)` cycles and the slice claims straight out of
this file and asserts them against `cube.py`, so a wrong direction fails the build
instead of quietly misleading the next session — which is exactly what it did until
these sentences were corrected. Keep the formats above intact: the parsers fail loudly
if they stop matching, rather than silently passing.

### Diagram output structure

Generated SVGs are organized in subdirectories under `guide/figures/generated/`:
- `oll/` — OLL case diagrams (plan-view, top-down)
- `pll/` — PLL case diagrams (plan-view with arrows)
- `oll-full/` — the full 57-OLL set (from `fullsets.py`)
- `pll-full/` — the full 21-PLL set (from `fullsets.py`)
- `notation/` — 3D isometric move notation diagrams, plus `overview.svg` (the six face turns on one cube) and its unreferenced backup `overview_hub.svg`
- `steps/` — 3D isometric step progress + case diagrams

## Writing Philosophy

The guide should be as small and concise as possible while containing all information needed to learn to solve the Rubik's cube well. The method progressively introduces as few new algorithms as possible at each phase while always being able to fully solve the cube. Prefer terse, information-dense prose over verbose explanations.

## Key Conventions

- `diagrams.py` defines `Y` (YELLOW) / `G` (GREY) shorthands for u_face color arrays, but they are
  largely vestigial: cases are derived through `_yellow_mask()`, and only `oll_solved` still
  writes `Y` literals. Derive, don't hand-write a mask.
- U-face indices are row-major: 0=TL, 1=TC, 2=TR, 3=ML, 4=Center, 5=MR, 6=BL, 7=BC, 8=BR. Top row = back of cube, bottom row = front.
- OLL cross algorithms: `F(R U R' U')F'` solves **Line** (hold horizontal), `f(R U R' U')f'` solves **Hook** (hold L in front-right).
- Ruff config: Python 3.12, line-length 100, rules E/F/I/UP/W.
- mypy: `strict` over `src/`, signatures not required in `tests/`; `svgwrite`
  has no stubs and is the one ignored import. Prefer a real annotation to a
  `type: ignore`, and if one is unavoidable make it per-code with a reason.
