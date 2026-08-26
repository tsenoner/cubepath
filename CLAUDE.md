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
make ci        # check + Playwright E2E (what GitHub Actions runs)
make build     # PDF guide + app
make diagrams  # regenerate SVG diagrams + sync into the app
```

Two gates, deliberately different: `make check` is fast and runs on every push;
`make ci` adds the Playwright E2E suite and runs in CI. Changing a command means
editing the Makefile — never re-list commands in the hook or the workflow.

Individual tools still run directly when working inside one subtree:

```bash
cd tools/diagrams
uv run cubepath-diagrams   # generate SVG diagrams
uv run cubepath-cheatcards # generate credit-card cheat sheets (Typst PDF)
uv run pytest tests/       # run tests
uv run pytest tests/test_diagrams.py::test_all_cases_count   # single test
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

**Prerequisites:** uv, pandoc (>=3.0), typst, Node >= 22.12 (app/)

**Local CI gate:** run `git config core.hooksPath .githooks` once per clone.
The pre-push hook runs `make check` — a push that would fail CI is rejected
locally.

## App (app/)

Astro + TypeScript strict PWA (offline-first). Commands, from `app/`:

```bash
npm run dev / build / preview
npx astro check          # strict type gate
npx vitest run           # every algorithm machine-verified on the cubing.js kpuzzle
npx playwright test      # smoke + airplane-mode E2E (the PWA gate)
node scripts/gen-cases.mjs      # regenerate src/data/fullsets.gen.ts + .rich.gen.ts
node scripts/extract-algs.mjs   # re-extract + verify the JPerm dataset (gated write)
node scripts/verify-f2l.mjs     # F2L-41 verifier
node scripts/verify-l2e.mjs     # 5x5 L2E verifier
node scripts/gen-icons.mjs      # rasterize the PWA icon set from favicon.svg
```

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

Data flow: `src/data/extracted/*.json` (verified extractions) → `gen-cases.mjs` →
`fullsets.gen.ts` (lean, ships to client) + `fullsets.rich.gen.ts` (recognition +
alternates, build-time only) → merged with curated entries in `src/data/algs.ts`
(`ALL_CASES`). Never hand-edit generated files; never retype algorithms — every
alg is kpuzzle-verified in `tests/algs.spec.ts`.

Deploys: Vercel project `cubepath` (team in docs/DECISIONS.md), git-linked via
the Vercel GitHub App — **every push to master auto-deploys** to
https://cubepath-six.vercel.app (root `vercel.json` builds from `app/`).
Manual fallback only: `scripts/build-deploy-payload.py` (refuses incomplete
file sets) + the Vercel MCP.

## Diagram pipeline (tools/diagrams/)

Python SVG generator + cube simulator feeding both the guide PDF and the app.

### Cube Simulator

`tools/diagrams/src/cubepath/cube.py` is a minimal Rubik's cube simulator (~220 lines). Used by tests to verify diagram sticker colors and algorithm correctness. State: 6 faces × 9 stickers (row-major). Table-driven moves (R/L/U/D/F/B/M/S/E + wide/rotations). Algorithm parser handles `R U R' U'`, `R2`, lowercase wide (`r`, `f`), and `(R U)×2` repeats. Coordinate mapping `diagram_to_sim(face, a, b)` bridges diagram coords to simulator state.

### Algorithm Data

`tools/diagrams/src/cubepath/algs.py` is the single source of truth for all algorithms. Diagrams derive their sticker states from these strings via the simulator; `tests/test_derivation.py` asserts the guide's tables match, arrows match the real piece permutation, and the 7 corner-orientation algs cover all 7 OCLL classes. Never hand-define sticker layouts — derive them.

### Diagram Pipeline

`tools/diagrams/src/cubepath/diagrams.py` defines all 17 cube diagrams as `CubeDiagram` dataclasses rendered to SVG using `svgwrite`. Case sticker data is **derived from algorithms** via `_derived_cross_case` / `_derived_oll_corner_case` / `_derived_pll_case` (OLL: yellow/grey masks; PLL: true colors). The entry point `cubepath-diagrams` writes to `guide/figures/generated/`.

Four case groups: `_oll_cross_cases()` (3), `_oll_corner_cases()` (8), `_pll_corner_cases()` (2), `_pll_edge_cases()` (4). OLL cases have no arrows; PLL cases use `swaps` (bidirectional) and `cycles` (directional) arrow fields — hand-declared for layout but permutation-verified by tests.

`StepDiagram` dataclasses produce 3D isometric progress/case diagrams: `_step_cases()` (8 steps), `_corner_case_steps()` (3), `_edge_case_steps()` (2), `_orient_corner_case()` (1), `_orient_corner_cases_15()` (2), `_corner_pos_case()` (1), `_align_edge_cases()` (2). Each specifies a solved-sticker set, optional face_colors override (e.g. flipped white-on-top), and sticker overrides for highlighting.

### Guide Build

`guide/cubepath.md` is the single source file. Pandoc builds PDF using `guide/defaults/pdf.yaml` (Typst output), passing through `guide/filters/callouts.lua`.

`cubepath-cheatcards` (`tools/diagrams/src/cubepath/cheatcards.py`) generates the credit-card cheat sheets from the canonical alg data (Typst, `typst compile --root guide/`) into `guide/build/cheat-cards.pdf`. Both PDFs also ship in-app from `app/public/` (`/cubepath.pdf`, `/cheat-cards.pdf`).

### Lua Filter (`guide/filters/callouts.lua`)

Handles three things:

1. **Callout divs** — Fenced divs with classes `.algorithm`, `.tip`, `.caution`, `.info` become styled Typst `#block()` markup.

2. **Steps div** — `:::: {.steps}` wraps the Phase 1 step tables in a mirrored 4-column Typst grid layout.

3. **Image rotation** — `![alt](path){ rotate=180 }` attribute wraps in `#box(width, rotate(..., image(...)))`. This keeps rotated images inline (important for side-by-side figure rows).

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

**Adjacency (CW from top):** Blue → Red → Green → Orange → Blue. So with Red in front: R=Green, L=Blue.

**3D isometric view** shows three faces: U (Yellow, top), F (Red, front-left), R (Green, front-right).

**Move rotation direction:** CW when looking at the face from outside. For the isometric projection:
- R CW from +x: top→front→bottom→back. In yz plane: (y, z) → (2−z, y).
- U CW from +y: front→right→back→left. In xz plane: similar.
- F CW from +z: top→right→bottom→left. In xy plane: similar.
- L/D follow opposite-face conventions. M follows L direction, S follows F direction, E follows D direction.

### Diagram output structure

Generated SVGs are organized in subdirectories under `guide/figures/generated/`:
- `oll/` — OLL case diagrams (plan-view, top-down)
- `pll/` — PLL case diagrams (plan-view with arrows)
- `notation/` — 3D isometric move notation diagrams
- `steps/` — 3D isometric step progress + case diagrams

## Writing Philosophy

The guide should be as small and concise as possible while containing all information needed to learn to solve the Rubik's cube well. The method progressively introduces as few new algorithms as possible at each phase while always being able to fully solve the cube. Prefer terse, information-dense prose over verbose explanations.

## Key Conventions

- The guide uses `Y` (YELLOW) and `G` (GREY) shorthand for u_face color arrays in diagrams.py.
- U-face indices are row-major: 0=TL, 1=TC, 2=TR, 3=ML, 4=Center, 5=MR, 6=BL, 7=BC, 8=BR. Top row = back of cube, bottom row = front.
- OLL cross algorithms: `F(R U R' U')F'` solves **Line** (hold horizontal), `f(R U R' U')f'` solves **Hook** (hold L in front-right).
- Ruff config: Python 3.12, line-length 100, rules E/F/I/UP/W.
