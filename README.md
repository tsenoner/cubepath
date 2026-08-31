# Cubepath

**Speedcubing from zero** — a free, offline-first course from absolute beginner to full CFOP, plus 4×4 and 5×5.

**Live:** [cubepath-six.vercel.app](https://cubepath-six.vercel.app) — installable, the whole course works offline. The printable guide ships in-app at `/cubepath.pdf`; the double-sided credit-card cheat sheet, print-ready sheets and a no-duplex fold-over version are at [`/print`](https://cubepath-six.vercel.app/print) (see [docs/printing.md](docs/printing.md)).

- `app/` — the web app (Astro + TypeScript, installable PWA)
- `tools/cubepath/` — build-time Python: cube simulator, SVG diagrams, card set, logo
- `guide/` — the printable PDF companion (Pandoc → Typst)
- `docs/` — decision log, printing and resource references (`docs/archive/` is finished work, kept for provenance)

## Commands

Prerequisites: [uv](https://docs.astral.sh/uv/), [pandoc](https://pandoc.org/) ≥ 3.1.2 (typst writer), [typst](https://typst.app/), [poppler](https://poppler.freedesktop.org/) (card build gates), Node ≥ 22.12

Run `make` on its own for the full list. The common ones:

```bash
make install     # install app + Python dependencies
make dev         # app dev server -> http://localhost:4321
make check       # local gate: ruff, pytest, astro check, vitest, build
make build       # diagrams, PDF guide, card set and the app
make diagrams    # regenerate the SVG diagrams into app/public/diagrams/
```

The `Makefile` is the single source of truth for this command surface — the
pre-push hook and CI call the same targets, so the local gate and the CI gate
cannot drift apart.

Working inside a single subtree? The underlying tools still run directly:

```bash
cd tools/cubepath && uv run pytest tests/    # verify algorithms + diagram derivation
cd app && npm run dev                        # app only
```

Every published algorithm is machine-verified against the bundled cube simulator,
and every case diagram is derived from its algorithm — a mismatch is a build
error, not a shipped bug. The same applies to the generated files the app ships:
the PDF, the 180 diagrams, the card PDFs and the favicon are each pinned to their
generator by a test, so `make check` fails rather than letting a stale artifact
reach production.

## License

Code: MIT. Course content (guide text, lessons): CC BY 4.0. See LICENSE.
