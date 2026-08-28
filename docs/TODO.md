# Open work

Completed items move to `docs/DECISIONS.md` with their rationale — this file
holds only what is still open.

- [ ] extend with different guides, can be found here: https://www.kungfoomanchu.com/home.html#333
- [ ] one physical diagram tree instead of two. `guide/figures/generated/` and
      `app/public/diagrams/` are the same 220 SVGs committed twice, kept in step by
      `scripts/sync-diagrams.sh` and a byte-identity test. A 2026-08-27 workflow
      prototyped three ways — `app/public/diagrams` as a git-tracked symlink to
      `guide/figures/generated` (needs a `core.symlinks=false` gate for Windows
      checkouts), a top-level `diagrams/` with an `app/scripts/sync-diagrams.mjs`,
      and a `scripts/build.sh` rework — and was abandoned uncommitted before the
      count went 130 → 220; the prototypes were deleted on 2026-08-28. If revisited,
      redo against the current tree; the symlink variant is ~3 source files.
