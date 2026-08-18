# Decision log — autonomous build

Decisions made during the autonomous PWA build (Aug 2026), beyond what the
master plan (docs/master-plan.html) and the user's locked answers specify.
User-locked: full M0–M6 scope · Vercel deploy · push to master per milestone ·
MIT code + CC BY 4.0 content · guide aesthetic · free subdomain · full big-cube
courses · PDF stays first-class.

## Quick-wins phase (guide v0.2)

- **All case diagrams are now derived from algorithms** via the simulator
  (`_derived_*` in diagrams.py), not hand-defined. Rationale: beyond the
  audit's F2/F3, mechanical checking found the shipped Pi diagram depicted an
  H-case rotation, Chameleon's diagram showed diagonal corners for an
  adjacent-corner alg, Bowtie's side stickers were wrong, and all six PLL
  diagrams had physically impossible side colors. Hand-drawn sticker data is
  banned from here on; `tests/test_derivation.py` enforces it.
- **Ua switched to the M-slice variant** `M2 U M U2 M' U M2` (was
  `R U' R U R U R U' R' U' R2`). The simulator proved both have the *identical*
  pre-state (same case, same angle), and the guide's own prose ("Ua, H-Perm,
  Z-Perm all use M") plus Phase 2's "Ua (M-slice version) in Phase 3" promise
  only hold for the M-slice form.
- **H case named "Double Headlights"** (not "H") to match the guide's
  recognition-first naming; the old (wrong) "Headlights" H-picture is reused
  for it, and "Headlights" got a newly derived U-case picture matching its alg.
- **Phase 3 count corrected to +10**: the old "+8" undercounted even before
  the H addition (9 new algs were listed).
- `src/cubepath/algs.py` is the single source of truth for algorithms; the
  guide's tables are tested against it (`test_guide_tables_match_canonical_algorithms`).
