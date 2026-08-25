# Cubepath

**Speedcubing from zero** — a free, offline-first course from absolute beginner to full CFOP, plus 4×4 and 5×5.

**Live:** [cubepath-six.vercel.app](https://cubepath-six.vercel.app) — installable, the whole course works offline. The printable guide and credit-card cheat sheets ship in-app at `/cubepath.pdf` and `/cheat-cards.pdf`.

- `app/` — the web app (Astro + TypeScript, installable PWA)
- `tools/diagrams/` — Python cube simulator + SVG diagram generator (build-time tooling)
- `guide/` — the printable PDF companion (Pandoc → Typst)
- `docs/` — master plan, decision log, resources

## Commands

Prerequisites: [uv](https://docs.astral.sh/uv/), [pandoc](https://pandoc.org/) ≥ 3.0, [typst](https://typst.app/), Node ≥ 22.12

Run `make` on its own for the full list. The common ones:

```bash
make install     # install app + Python dependencies
make dev         # app dev server -> http://localhost:4321
make check       # local gate: ruff, pytest, astro check, vitest, build
make build       # PDF guide -> guide/build/cubepath.pdf, plus the app
make diagrams    # regenerate SVG diagrams and sync them into the app
```

The `Makefile` is the single source of truth for this command surface — the
pre-push hook and CI call the same targets, so the local gate and the CI gate
cannot drift apart.

Working inside a single subtree? The underlying tools still run directly:

```bash
cd tools/diagrams && uv run pytest tests/   # verify algorithms + diagram derivation
cd app && npm run dev                       # app only
```

Every published algorithm is machine-verified against the bundled cube simulator,
and every case diagram is derived from its algorithm — a mismatch is a build
error, not a shipped bug.

## License

Code: MIT. Course content (guide text, lessons): CC BY 4.0. See LICENSE.
