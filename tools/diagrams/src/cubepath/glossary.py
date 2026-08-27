"""Card vocabulary: what gets glossed, what is banned, and what stays plain.

Three tiers, and the middle one is the reason this file exists as data rather
than as a style note nobody re-reads:

*   **TEACH** — a term a learner will meet elsewhere (in a video, on a forum,
    in the app). Keep it, and gloss it in a handful of words **on every card
    that uses it**. Not "defined earlier in the set": a term defined on Card 1
    is forgotten by Card 3, and the annex is the card people cut off first.
    The redundancy is the design.
*   **BAN** — insider shorthand with an equally standard plain phrase. The
    plain phrase wins; `cheatcards.gate_card` fails the build if a banned term
    reaches a rendered card.
*   **PLAIN** — never introduce the term at all; say the thing instead.
    Gated alongside BAN, for the same reason: a tier nothing enforces is a
    style note, and this file exists precisely to not be one.
"""

from __future__ import annotations

# term -> gloss, six words or so. Printed under a WORDS header.
GLOSS: dict[str, str] = {
    "algorithm": "a fixed sequence of turns",
    "trigger": "a short algorithm your hands run as one unit",
    "sexy move": "the R U R' U' trigger",
    "sledgehammer": "the R' F R F' trigger",
    "Sune": "the one-yellow-corner algorithm, used on every card after Card 1",
    "OLL": "make the whole top face yellow",
    "PLL": "slide the top pieces home",
    "headlights": "two matching corners on one face",
    "AUF": "the free top turn that lines a case up",
    "parity": "a case a 3x3 cannot have",
    "edge pair": "two edges glued into one, on a 4x4 or 5x5",
    "F2L": "first two layers, solved as pairs",
    "look-ahead": "watching the next piece while your hands finish this one",
    "adjacent corner swap": "the swapping corners share an edge",
    "diagonal corner swap": "the swapping corners sit opposite",
}

# Terms that must carry their gloss on EVERY card that uses them (F13). These
# are the ones a learner meets elsewhere and cannot guess: a card defined only
# on Card 1 is forgotten by Card 3, and the annex is the card people cut off.
TEACH: frozenset[str] = frozenset(
    {
        "OLL",
        "PLL",
        "headlights",
        "AUF",
        "parity",
        "edge pair",
        "F2L",
        "look-ahead",
        "adjacent corner swap",
        "diagonal corner swap",
    }
)

# Terms the card defines by *showing* rather than by saying: the footer legend
# on every card front prints a colour swatch, the literal algorithm and the
# name together, which is a better definition than any six words. They still
# get a prose gloss where there is room, but it is not required twice.
DEMONSTRATED: frozenset[str] = frozenset({"sexy move", "Sune", "sledgehammer"})

# banned term -> what to write instead. Matched case-insensitively on word
# boundaries against the text extracted from every rendered card.
BANNED: dict[str, str] = {
    "dedge": "edge pair",
    "alg": "algorithm",
    "algs": "algorithms",
    "token": "move",
    "lights": "headlights",
    "regrip": "change grip",
    "OCLL": "(delete)",
    "2GLL": "(delete)",
    "duplex": "two-sided",
    "inner slice": "2nd layer only",
    "colour": "color",
    "colours": "colors",
    "centre": "center",
    "centres": "centers",
    "anti-clockwise": "counter-clockwise",
    "CW": "clockwise",
    "CCW": "counter-clockwise",
}

# Terms never to introduce: say the right-hand side instead. Enforced by
# `cheatcards.gate_card` on the text of every rendered card, same as BANNED.
PLAIN: dict[str, str] = {
    "permute": "slide the pieces home",
    "orient": "make the top all yellow",
    "reduction": "the three-arrow recipe already printed",
}


def gloss_line(*terms: str) -> str:
    """The WORDS block for one card, as a single sentence run."""
    missing = [t for t in terms if t not in GLOSS]
    if missing:
        raise KeyError(f"no gloss for {missing} — add it to GLOSS or use a plain phrase")
    return " · ".join(f"{t} = {GLOSS[t]}" for t in terms)
