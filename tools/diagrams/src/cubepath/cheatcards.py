"""Printable credit-card cheat sheets, generated from the canonical alg data.

Emits guide/build/cheat-cards.typ + compiles it with Typst to a PDF of
credit-card-sized (85.6 × 54 mm) cards: 2-look OLL on one card, 2-look PLL on
the next, each with its case diagrams. Run via `uv run cubepath-cheatcards`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from cubepath.algs import ALGORITHMS

_REPO = Path(__file__).resolve().parents[4]
_FIGS = _REPO / "guide" / "figures" / "generated"
_OUT = _REPO / "guide" / "build"

# (svg relative to figures/generated, display name, algorithm-key)
OLL_CARD_A = [
    ("oll/oll_line.svg", "Line", "F-sexy-F'"),
    ("oll/oll_hook.svg", "Hook", "f-sexy-f'"),
    ("oll/oll_sune.svg", "Sune", "Sune"),
    ("oll/oll_antisune.svg", "Anti-Sune", "Anti-Sune"),
]

OLL_CARD_B = [
    ("oll/oll_pi.svg", "Pi", "Pi"),
    ("oll/oll_headlights.svg", "Headlights", "Headlights"),
    ("oll/oll_double_headlights.svg", "Dbl Headlights", "Double Headlights"),
    ("oll/oll_chameleon.svg", "Chameleon", "Chameleon"),
    ("oll/oll_bowtie.svg", "Bowtie", "Bowtie"),
]

PLL_CARD = [
    ("pll/pll_tperm.svg", "T-Perm", "T-Perm"),
    ("pll/pll_yperm.svg", "Y-Perm", "Y-Perm"),
    ("pll/pll_ub.svg", "Ub", "Ub"),
    ("pll/pll_ua.svg", "Ua", "Ua"),
    ("pll/pll_hperm.svg", "H-Perm", "H-Perm"),
    ("pll/pll_zperm.svg", "Z-Perm", "Z-Perm"),
]


def _card(title: str, rows: list[tuple[str, str, str]]) -> str:
    body_rows = ",\n".join(
        f'    image("../figures/generated/{svg}", width: 6.5mm), '
        f'text(size: 5.4pt, weight: "bold")[{name}], '
        f'text(size: 5.6pt, font: "Courier New", weight: "bold")[{ALGORITHMS[key]}]'
        for svg, name, key in rows
    )
    return f"""#page(width: 85.6mm, height: 54mm, margin: 2.5mm)[
  #text(size: 7pt, weight: "bold")[{title}]
  #v(0.2mm)
  #grid(
    columns: (7mm, 15.5mm, 1fr),
    column-gutter: 1.2mm,
    row-gutter: 0.4mm,
    align: (center + horizon, left + horizon, left + horizon),
{body_rows}
  )
  #place(bottom + right, text(size: 4.5pt, fill: luma(120))[cubepath — \
cubepath-six.vercel.app])
]"""


def main() -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    typ = _OUT / "cheat-cards.typ"
    typ.write_text(
        "\n".join(
            [
                '#set text(font: "Libertinus Serif")',
                _card("2-Look OLL 1/2 — cross, then corners", OLL_CARD_A),
                _card("2-Look OLL 2/2 — corner cases", OLL_CARD_B),
                _card("2-Look PLL — permute the last layer", PLL_CARD),
            ]
        )
    )
    pdf = _OUT / "cheat-cards.pdf"
    subprocess.run(
        ["typst", "compile", "--root", str(_REPO / "guide"), str(typ), str(pdf)], check=True
    )
    print(f"cheat cards: {pdf}")


if __name__ == "__main__":
    main()
