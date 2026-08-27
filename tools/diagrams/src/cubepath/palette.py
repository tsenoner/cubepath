"""Print palettes — the single source of truth for the guide and the cards.

Trigger colours below are shared with `guide/filters/callouts.lua`; the
greyscale helpers at the bottom are what every printed palette is chosen
against, including the card face colours in `diagrams.CARD_FACES`.

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

# The canonical trigger of each family: the move string the card footers print
# in the legend, and the name the cards call it by. `glossary.DEMONSTRATED`
# names these same three as "defined by showing rather than saying", and
# `cheatcards._footer` builds the legend from here — so the claim and the
# legend cannot come apart.
FAMILIES: dict[str, tuple[str, str]] = {
    "r": ("R U R' U'", "sexy move"),
    "g": ("R U R' U", "Sune"),
    "b": ("R' F R F'", "sledgehammer"),
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


# ── Greyscale legibility ──────────────────────────────────────────────
# A card is printed, often on a mono laser. Two stickers that differ only in
# hue become the same grey, so every printed palette is chosen against these
# two functions and gated by `tests/test_diagrams.py` — never by eye.


def relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance. This is what a mono printer sees."""
    h = hex_color.lstrip("#")
    channels = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two colours, 1.0 (identical) to 21.0."""
    lo, hi = sorted((relative_luminance(a), relative_luminance(b)))
    return (hi + 0.05) / (lo + 0.05)


def lstar_grey(lstar: float) -> int:
    """CIE L* -> the 8-bit sRGB grey with that lightness.

    The card identity bands are specified as a lightness ramp, because that is
    what survives a photocopier. Keeping the ramp as L* and converting here
    means a new card declares a lightness rather than looking a byte up in a
    table only the four existing cards appear in.
    """
    y = ((lstar + 16) / 116) ** 3 if lstar > 8 else lstar / 903.3
    channel = 12.92 * y if y <= 0.0031308 else 1.055 * y ** (1 / 2.4) - 0.055
    return round(channel * 255)
