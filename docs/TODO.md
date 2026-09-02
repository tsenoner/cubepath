# Open work

Completed items move to `docs/DECISIONS.md` with their rationale — this file
holds only what is still open.

- [ ] extend with different guides, can be found here: https://www.kungfoomanchu.com/home.html#333
- [ ] /reference's Yellow Cross section: the Hook and Dot rows carry the Phase 1.5 wide-f
      algorithms while "Taught in" points at the Phase 1 lesson (two and three passes of
      F-sexy-F', different hold), and the Hook icon is drawn for the Phase 1 back-left hold
      beside a cue saying front-right. Found 2026-09-02; see DECISIONS.md § "The beginner
      method is on /reference in full now".
- [ ] `app/src/data/extracted/stages.json` is the one generated artifact with no
      regenerate-and-compare gate. Every other row of CLAUDE.md's "Generated artifacts"
      table is pinned by a test; this one is only read, never checked, so a hand edit with
      a different stage value passes `make check` and is silently reverted by the next
      `npm run gen:stickering`. `test_cards.py::test_committed_cards_json_matches_the_generator`
      is the pattern to copy — or give `gen-stickering.mjs` a `--check` flag and wire it into
      `verify:data`. Found 2026-09-02.
- [ ] `pythonAlgorithm()` in `app/tests/algs.spec.ts` regex-scrapes `algs.py`'s SOURCE TEXT
      from TypeScript — the cross-language coupling `notation.py` records the repo
      deliberately removing in the other direction ("nothing here parses JavaScript any
      more … they now arrive as data"). It breaks on anything the line pattern misses: a
      `ruff format` wrap of a long entry, an escaped quote, a concatenated value. The fix is
      to emit `ALGORITHMS` as JSON the way `cards.json` is emitted, with a
      `matches_the_generator` twin, and delete the parser. Found 2026-09-02.
- [ ] Phase 1.5's algorithm count is stated three ways: the speed-tricks description ("not
      one new algorithm to learn") and orient-corners.mdx ("zero new algorithms") say zero;
      the guide's Phase 1.5 heading and a DECISIONS entry say one (the wide-f Hook); the
      machine-checked progression table (and now /reference) say three. Decide which is the
      claim and make the prose match. Same DECISIONS entry.
