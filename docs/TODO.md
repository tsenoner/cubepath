# Open work

Completed items move to `docs/DECISIONS.md` with their rationale — this file
holds only what is still open.

- [ ] extend with different guides, can be found here: https://www.kungfoomanchu.com/home.html#333
- [ ] `pythonAlgorithm()` in `app/tests/algs.spec.ts` regex-scrapes `algs.py`'s SOURCE TEXT
      from TypeScript — the cross-language coupling `notation.py` records the repo
      deliberately removing in the other direction ("nothing here parses JavaScript any
      more … they now arrive as data"). It breaks on anything the line pattern misses: a
      `ruff format` wrap of a long entry, an escaped quote, a concatenated value. The fix is
      to emit `ALGORITHMS` as JSON the way `cards.json` is emitted, with a
      `matches_the_generator` twin, and delete the parser. Found 2026-09-02.
