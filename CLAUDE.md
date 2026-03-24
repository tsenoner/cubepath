# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands

```bash
# Full build: generate diagrams + PDF
bash scripts/build.sh

# Generate SVG diagrams only
uv run cubepath-diagrams

# Run tests
uv run pytest tests/

# Run a single test
uv run pytest tests/test_diagrams.py::test_all_cases_count

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/
```

**Prerequisites:** uv, pandoc (>=3.0), typst

## Architecture

This is a Rubik's Cube guide with a Python SVG diagram pipeline and Pandoc-based PDF output (via Typst).

### Diagram Pipeline

`src/cubepath/diagrams.py` defines all 16 cube diagrams as `CubeDiagram` dataclasses (u_face colors, side strips, optional PLL arrows) and renders them to SVG using `svgwrite`. The entry point `cubepath-diagrams` writes to `guide/figures/generated/`.

Four case groups: `_oll_cross_cases()` (3), `_oll_corner_cases()` (7), `_pll_corner_cases()` (2), `_pll_edge_cases()` (4). OLL cases have no arrows; PLL cases use `swaps` (bidirectional) and `cycles` (directional) arrow fields.

`StepDiagram` dataclasses produce 3D isometric progress/case diagrams: `_step_cases()` (8 steps), `_corner_case_steps()` (3), `_edge_case_steps()` (2), `_orient_corner_case()` (1), `_orient_corner_cases_15()` (2), `_corner_pos_case()` (1), `_align_edge_cases()` (2). Each specifies a solved-sticker set, optional face_colors override (e.g. flipped white-on-top), and sticker overrides for highlighting.

### Guide Build

`guide/cubepath.md` is the single source file. Pandoc builds PDF using `guide/defaults/pdf.yaml` (Typst output), passing through `guide/filters/callouts.lua`.

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
- L/D follow opposite-face conventions. M follows L direction.

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
