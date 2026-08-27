# cubepath diagrams

Build-time tooling: cube simulator + SVG case/step diagram generator.

- `src/cubepath/algs.py` — canonical algorithm data (single source of truth)
- `src/cubepath/cube.py` — minimal 3×3 simulator used to verify algorithms and derive diagram states
- `src/cubepath/diagrams.py` — SVG generator; all case sticker data derived from algorithms

```bash
uv run cubepath-diagrams   # writes guide/figures/generated/
uv run pytest tests/
uv run ruff check src/ tests/
```
