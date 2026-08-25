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

## Design phase

- **Static hi-fi mockups** (not clickable prototypes) on the design canvas —
  the product itself is built in code; the canvas exists to react to visual
  direction. Published as "Cubepath UI System"
  (https://claude.ai/code/artifact/a42873c4-ee91-4882-90e5-dbffac7b4fb8).
- **Type**: Newsreader (headings) + IBM Plex Sans (body) + IBM Plex Mono
  (algorithms), all Google Fonts with metric-close fallbacks.
- **Tokens**: warm paper #FCFBF8 / ink #1C1917, accent #1565C0 (the guide's
  algorithm-callout blue), ok #2E7D32, warn #E65100; cube colors and trigger
  colors (trig-r/g/b) carried over verbatim from the pipeline; dark theme
  counterparts defined in design/build_canvas.py.
- **Signature elements**: trigger-colored monospace algorithms, real derived
  case diagrams inline, guide callout system on the web, case-row anatomy
  (diagram / name+recognition / alg / status / play).
- design/ holds the generator (build_canvas.py) + artboards; re-run and
  re-seed to update the canvas.

## M0

- **Worker-safe preload helper**: Rolldown-Vite 8 bundles its preload helper
  (which touches `document`) into cubing.js's search-worker chunk, killing
  on-device scrambles in production builds (vitejs/vite#14499 class;
  `build.modulePreload` doesn't govern worker chunks). Fixed with a small
  Astro `astro:build:done` integration that guards the helper's DOM branch
  behind `typeof document`. The integration throws if Vite's helper shape
  changes, and the Playwright smoke test proves scrambles + both players
  in every build.
- twisty-player uses a **closed** shadow root — E2E asserts rendering via the
  element's own `experimentalScreenshot()` instead of DOM probing.

## Deploys

- The Vercel **GitHub App is not installed** on the user's GitHub account
  (interactive web authorization required — cannot be done autonomously), and
  the local Vercel CLI token is expired. Deploys therefore go through the
  authenticated Vercel MCP (`deploy_to_vercel`, source-file deploys) per
  milestone. Production alias: https://cubepath-six.vercel.app.
  TODO for the user: install https://github.com/apps/vercel on tsenoner/cubepath
  and link the project (Root Directory = `app`) for automatic git deploys.
- Vercel Deployment Protection (SSO) disabled on the project — required for a
  public PWA and service-worker testing.

## M3

- **JPerm's f2l/2loll/2lpll lib files 404** (verified 2026-08-19:
  jperm.net/lib/{f2l,2loll,2lpll}.js all return HTTP 404), so the 41 F2L cases
  will be sourced semi-manually from JPerm's Best-F2L PDF in M3 (per the
  research brief §8); the extractor covers oll/pll/4x4oll/4x4pll only.

## M5/M6

- **F2L-41 dataset**: JPerm Best-F2L PDF algs mapped to SCDB numbering purely
  mechanically (kpuzzle case-class matching); 14 PDF algs excluded on
  principle (multi-slot or left-slot executions). 105 algs verified.
- **5×5 L2E**: 13 cases (SCDB is right, not 12); invariant allows rigid
  transport of intact non-target edge groups (harmless during reduction);
  4×4-vs-5×5 parity confusion regression-tested.
- **i18n**: v1 ships EN-only; the content collection layout (one MDX per
  lesson, typed data separate from prose) is the i18n-ready structure the
  plan asked for — a locale dimension can be added to the collection without
  restructuring.
- Cheat cards ship both in guide/build (source of truth) and app/public.
