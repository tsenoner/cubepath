# Cubepath

**Speedcubing from zero** — a free, offline-first course from absolute beginner to full CFOP, plus 4×4 and 5×5.

- `app/` — the web app (Astro + TypeScript, installable PWA) *(in progress)*
- `tools/diagrams/` — Python cube simulator + SVG diagram generator (build-time tooling)
- `guide/` — the printable PDF companion (Pandoc → Typst)
- `docs/` — master plan, decision log, resources

## Build the PDF guide

Prerequisites: [uv](https://docs.astral.sh/uv/), [pandoc](https://pandoc.org/) ≥ 3.0, [typst](https://typst.app/)

```bash
bash scripts/build.sh          # diagrams + PDF -> guide/build/cubepath.pdf
```

## Python tooling

```bash
cd tools/diagrams
uv run cubepath-diagrams       # regenerate guide/figures/generated/
uv run pytest tests/           # verify algorithms + diagram derivation
```

Every published algorithm is machine-verified against the bundled cube simulator,
and every case diagram is derived from its algorithm — a mismatch is a build
error, not a shipped bug.

## License

Code: MIT. Course content (guide text, lessons): CC BY 4.0. See LICENSE.
