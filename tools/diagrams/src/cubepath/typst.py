"""Typst rendering primitives shared by the card content and the imposition.

Kept separate so `cards.py` (what a card says) and `cheatcards.py` (how sheets
are laid out and gated) can both use them without importing each other.

The one rule worth remembering when editing card markup: `#f(...)` is for
*markup* position (inside `[...]`), and bare `f(...)` is for *code* position
(inside another call's arguments). Typst reports the mistake as "the character
`#` is not valid in code", which does not obviously mean "you nested it".
"""

from __future__ import annotations

from cubepath.notation import CHUNKS, Chunk, compact, family

_COLOR_FN = {"r": "r", "g": "g", "b": "b"}


def prime(text: str) -> str:
    """Bind each prime to its move letter. `pr()` (not `pr`) so the call ends
    the identifier — `#prU` would parse as a variable named `prU`."""
    return text.replace("'", "#pr()")


def _segment(seg: str, compacted: bool) -> str:
    text = prime(compact(seg) if compacted else seg)
    fn = _COLOR_FN.get(family(seg) or "")
    return f"#{fn}[{text}]" if fn else text


def _chunk(chunk: Chunk, compacted: bool) -> str:
    joiner = "" if compacted else " "
    body = joiner.join(_segment(s, compacted) for s in chunk)
    return f"[{body}]"


def alg(chunks: list[Chunk], compacted: bool = True, size: str = "AS") -> str:
    """Typst call rendering one algorithm as gap-separated chunks.

    A spaced block needs the wider gap: its chunks already contain ordinary
    spaces, which a 0.55em break would not beat.
    """
    fn = "a" if compacted else "aw"
    return f"#{fn}({size}, {', '.join(_chunk(c, compacted) for c in chunks)})"


def key_alg(name: str, **kw) -> str:
    return alg(CHUNKS[name], **kw)


# Characters Typst reads as markup. Underscore matters more than it looks:
# a write-in blank like "My target: ______" is emphasis syntax, and Typst only
# *warns* about it — which the build treats as an error, so it surfaces.
_MARKUP = "#@*_$`"


def esc(s: str) -> str:
    """Escape Typst markup characters in prose."""
    for ch in _MARKUP:
        s = s.replace(ch, "\\" + ch)
    return s


def diagram(svg: str, size: str, rotate: int = 0) -> str:
    return f'dia("{svg}", {size}, rot: {rotate}deg)' if rotate else f'dia("{svg}", {size})'
