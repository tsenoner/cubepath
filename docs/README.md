# docs/

Two tiers, so a reader can tell current from historical at a glance.

## Live reference — read these

| file | what it is |
| --- | --- |
| [`DECISIONS.md`](DECISIONS.md) | Append-only decision log. The one document that is always current; every non-obvious choice in the repo is justified here. |
| [`printing.md`](printing.md) | Print / duplex / lamination guidance for the card set. Mirrored by the app's `/print` page (`app/src/pages/print.astro`). |
| [`resources.md`](resources.md) | External method, algorithm and prior-art references. |
| [`TODO.md`](TODO.md) | Open work only. Completed items move into `DECISIONS.md`. |
| [`redesign-plan.html`](redesign-plan.html) | The presentation-layer plan from the 2026-08-27 audit: design system, case-presentation tiers, navigation, and the sequenced backlog. Open it in a browser. |
| [`research/tech-brief.md`](research/tech-brief.md) | The M0 integration brief. Still live: `app/scripts/extract-algs.mjs` and `verify-l2e.mjs` pin their big-cube algorithm strings to its §8. |

## `archive/` — finished, kept for provenance

Nothing here describes the project as it is. Each file carries a banner saying
what superseded it. They are retained rather than deleted because live code or
the decision log cites them.

| file | why it is kept |
| --- | --- |
| [`archive/card-set-plan.md`](archive/card-set-plan.md) | Executed plan for the shipped card set. `cubepath/cards.py` and `cubepath/cheatcards.py` cite its section numbers. |
| [`archive/master-plan.html`](archive/master-plan.html) | The 2026-08-19 build plan. Referenced by `DECISIONS.md`'s opening paragraph. |
| [`archive/design/`](archive/design/) | The one-time design-canvas generator. `tokens.css` is the live source of truth — see the README there for the drift. |

`other_guides/` is git-ignored: third-party reference PDFs, not ours to
redistribute.
