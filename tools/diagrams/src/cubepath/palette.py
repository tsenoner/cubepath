"""Trigger colours — the single source of truth for the guide and the cards.

`guide/filters/callouts.lua` renders the same three families in the guide PDF;
`tests/test_notation.py` asserts the Lua hexes still match these, so the two
cannot drift.

The hexes are deliberately dark. The guide's original triad (#D32F2F /
#2E7D32 / #1565C0) converts to luma 96/93/88 — *lighter* than the black body
text around it, so on a mono printer the triggers you most want to grab came
out faded. These land near-black in greyscale.
"""

from __future__ import annotations

# family letter -> hex, no leading '#'
TRIGGER_COLORS: dict[str, str] = {
    "r": "A61B1B",  # sexy family:   R U R' U'
    "g": "1B5E20",  # sune trigger:  R U R' U
    "b": "12408C",  # sledgehammer:  R' F R F'
}

# Exact token strings that belong to each family. A span is coloured if and
# only if its token string is a key here — colour is never hand-assigned.
FAMILY: dict[str, str] = {
    "R U R' U'": "r",
    "r U R' U'": "r",
    "L' U' L U": "r",
    "R U R' F'": "r",
    "R' D' R D": "r",
    "D' R' D R": "r",
    "R U R' U": "g",
    "R' F R F'": "b",
    "F R F'": "b",
    "R' F": "b",
}

# Prose labels the guide colours as a family name rather than a move string
# ("the [sexy move]{.trig-r}"). Listed so the guide-drift test can tell a
# deliberate label from a mis-tagged algorithm.
FAMILY_LABELS: dict[str, str] = {
    "sexy move": "r",
    "righty": "r",
}
