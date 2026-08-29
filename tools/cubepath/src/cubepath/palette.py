"""The colour vocabulary shared by the guide PDF, the cards and the app.

One definition, two renderings. Every colour the guide's Lua filter draws and
every colour `app/src/components/{Callout,AlgText}.astro` draws is declared
once, here, together with the `app/src/styles/tokens.css` custom property it
mirrors. Neither consumer can read this module at build time — one is Lua, one
is CSS — so `tests/test_notation.py` reads all three files and asserts they
still spell the same values. That gate, not a comment, is what keeps them
together.

Print is allowed to differ from screen, but only where a *stated* reason makes
the same value wrong on paper, and only in the two places below:

1. `TRIGGER_COLORS` vs `SCREEN_TRIGGER_COLORS`. A trigger span sits inline in a
   line of black monospace, so its greyscale weight is read against the tokens
   either side of it. The screen triad converts to luma 111/109/102 against
   body ink at 31 — *lighter* than the text around it, so on a mono printer the
   triggers you most want to grab came out faded. The print triad lands at
   85/82/69 (7.5–9.8:1 on white). The darkening is hand-tuned per hue, not a
   formula, and `test_print_triad_is_darker_than_the_screen_triad` pins the
   relation in both directions.

2. `PRINT_TINT`. A callout tint is defined by its relation to the page, not by
   its absolute value, and the two pages differ: the app's `--paper` is
   off-white (#fcfbf8) so `.info` lifts off it with a white `--card`, while the
   guide prints on pure white, where a lift does not exist. Only that one
   substitution is licensed, and it is keyed by token name so a second one
   cannot be added by accident.

Nothing else forks. A callout label owns its block — it is bold, uppercase and
alone on its line above a tint with a 4pt rule — so it competes with no body
text for greyscale rank, and inherits the screen value unchanged. The
greyscale helpers at the bottom are what every printed palette is chosen
against, including the card face colours in `diagrams.CARD_FACES`.
"""

from __future__ import annotations

from dataclasses import dataclass

# family letter -> hex, no leading '#'. Print; see deviation 1 above.
TRIGGER_COLORS: dict[str, str] = {
    "r": "A61B1B",  # sexy family:   R U R' U'
    "g": "1B5E20",  # sune trigger:  R U R' U
    "b": "12408C",  # sledgehammer:  R' F R F'
}

# The same three families on screen, mirroring tokens.css `--trig-*`. Declared
# here so "deliberately darkened for print" is a tested relation between two
# named triads instead of a sentence in a docstring that a future session can
# read as an accident and "fix".
SCREEN_TRIGGER_COLORS: dict[str, str] = {
    "r": "D32F2F",  # tokens.css :root --trig-r
    "g": "2E7D32",  # tokens.css :root --trig-g
    "b": "1565C0",  # tokens.css :root --trig-b
}

# Dark theme. Screen-only by definition: there is no dark paper.
DARK_TRIGGER_COLORS: dict[str, str] = {
    "r": "EF6B62",  # tokens.css [data-theme="dark"] --trig-r
    "g": "7CC47F",  # tokens.css [data-theme="dark"] --trig-g
    "b": "6FAAE8",  # tokens.css [data-theme="dark"] --trig-b
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


# ── Callouts ──────────────────────────────────────────────────────────
# The guide (`guide/filters/callouts.lua`) and the app
# (`app/src/components/Callout.astro`) render the same four callouts with the
# same anatomy: a tint, a 4pt/4px left rule, and a bold uppercase label. One
# definition for both, and one colour — `ink` — for the rule and the label,
# because a rule in a second hue is a second thing to keep true. The Material
# 500 borders this replaced measured 2.16–3.12:1 on white, three of them below
# WCAG 1.4.11's 3:1 floor for a non-text UI component.


@dataclass(frozen=True)
class Callout:
    """One callout type, in both renderings.

    `tint_token` / `ink_token` name the tokens.css light-theme custom property
    each hex mirrors; `tests/test_notation.py` resolves them against the real
    stylesheet, so the app can restyle a callout only by moving the token both
    sides already share. Dark mode needs no entry here: the app reads the same
    two token names, and the dark block redefines them.
    """

    label: str
    tint: str  # background, hex without '#'
    tint_token: str
    ink: str  # the left rule *and* the label
    ink_token: str


CALLOUTS: dict[str, Callout] = {
    "algorithm": Callout("Algorithm", "E8F4FD", "--accent-soft", "1565C0", "--accent"),
    "tip": Callout("Tip", "E8F5E9", "--ok-soft", "2E7D32", "--ok"),
    "caution": Callout("Caution", "FFF3E0", "--warn-soft", "B23C00", "--warn"),
    "info": Callout("Info", "FFFFFF", "--card", "57534E", "--soft"),
}

# Deviation 2 (see the module docstring): the only token whose screen value is
# a lift off an off-white --paper rather than an absolute surface. The guide
# prints on pure white, where that lift does not exist, so the print rendering
# recesses instead. Keyed by token name so the licence covers this one case.
PRINT_TINT: dict[str, str] = {"--card": "F5F5F5"}


def print_tint(callout: Callout) -> str:
    """The tint the guide PDF fills, after the one licensed substitution."""
    return PRINT_TINT.get(callout.tint_token, callout.tint)


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
