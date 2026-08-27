# Design canvas — ARCHIVED (2026-08-19), superseded by `app/src/styles/tokens.css`

`build_canvas.py` generated the seven `.dc.html` artboards for the one-time
visual-direction pass recorded in `docs/DECISIONS.md` § Design phase (published
canvas: <https://claude.ai/code/artifact/a42873c4-ee91-4882-90e5-dbffac7b4fb8>).
That direction shipped into `tokens.css`, `Header.astro` and the components.

**It is not a source of truth and must not be re-run to "update" the app.** The
live tokens have moved past it — measured, not guessed:

| token | `build_canvas.py` | live `tokens.css` |
| --- | --- | --- |
| `--line` | `#E7E4DE` | `#948f86` (retuned to clear 3:1) |
| `--faint` | `#8A857D` | `#79736a` (retuned to clear 4.5:1) |
| `--logo-body/-u/-f/-r` | absent | present (four tokens) |

Kept as archive rather than deleted because it is the provenance record for
the type and colour choices in the decision log. Three consequences of the
archive, all deliberate:

- Nothing in the repo references the artboards or `canvas.json` (verified:
  `git grep -F canvas.json` and `git grep -F .dc.html` are both empty).
- It is outside every gate — `make check-py` lints and tests only
  `tools/*/src` and `tools/*/tests` — so `build_canvas.py`'s import of
  `cubepath.algs` / `cubepath.cube` will rot on the next rename there. That is
  acceptable for an archived file and is *why* it is archived rather than
  wired into a gate: gating it would pin live code to a dead exploration.
- Its `sys.path` line still points at the pre-rename `tools/diagrams/src`.
