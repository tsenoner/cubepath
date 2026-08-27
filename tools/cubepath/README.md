# cubepath — build-time Python tooling

One `uv` project, package `cubepath`, four entry points. It was called
`tools/diagrams/` until the card set and the logo generator landed here too;
the directory now matches the package name.

Everything published — every algorithm, every diagram, every line on a card —
is **derived** from `algs.py` through the simulator. Nothing here re-types a
cube state or a colour, and the tests fail the build when a committed artifact
stops matching its generator.

## Modules

| module | owns |
| --- | --- |
| `algs.py` | canonical algorithm data — the single source of truth |
| `cube.py` | minimal 3×3 simulator; verifies algorithms and derives diagram states |
| `diagrams.py` | SVG generator for the guide's core case/step/notation figures |
| `fullsets.py` | the full 57-OLL / 21-PLL SVG sets, from the app's verified extraction |
| `notation.py` | algorithm → printable chunks |
| `cards.py` | what each card *says* — the deck table and the four cards' content |
| `cheatcards.py` | card imposition, build gates, CLI, `manifest.json` |
| `recognition.py` | PLL cues and Sune counts, derived from the cube state |
| `glossary.py` | vocabulary tiers; `BANNED` + `PLAIN` gated on every rendered card |
| `palette.py` | colours, measured against contrast rather than chosen |
| `typst.py` | algorithm → Typst markup, shared by `cards.py` and `cheatcards.py` |
| `logo.py` | the brand mark; source of truth for `app/public/favicon.svg` |

## Commands

```bash
uv run cubepath-diagrams   # SVGs -> guide/figures/generated/ (make diagrams also syncs into the app)
uv run cubepath-cards      # card set -> guide/build/cards/ (needs typst + poppler)
uv run cubepath-logo       # favicon.svg -> app/public/
uv run pytest tests/
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

`make check-py` from the repo root runs the ruff and pytest lines above; that
is what CI runs and what the pre-push hook gates on.
