"""Derived recognition data: what you look at to name a case.

Every fact here is read off the simulator state the printed algorithm solves,
never written down by hand. That is the same rule the diagrams follow, and it
is what lets a printed cue be tested: `tests/test_recognition.py` asserts the
derivation reproduces JPerm's own case classification for all 21 PLLs, that
every signature is unique, and that every cue fits the card.

**What is derived and what is not.** The *facts* are derived — which faces
show a bar, headlights or a matching pair, and how the edges cycle. The
English phrasing is a fixed template applied to those facts. So a wrong cue
is a template bug, never a mis-copied case.

**Recognition is closed-world, and that is not a detail.** For ten of the 21
cases there is *no* subset of positive facts that identifies them, because
another case has all of those facts and more: `Ga` is exactly
`L headlights + F right-pair`, while `Aa` is that *plus* `R right-pair`. A
cue must therefore state the whole signature — "this and nothing else" — not
a minimal distinguishing clause. Cues built from positive clauses alone would
be ambiguous for F, Ra, Rb, Ga, Gb, Gc, Gd and the four edges-only cases.
"""

from __future__ import annotations

import functools
from collections import deque

from cubepath.algs import ALGORITHMS
from cubepath.cube import state_before

# `_u_layer_views` lives in diagrams; import it from its home module rather
# than through fullsets, which only re-exports it by accident of import.
from cubepath.diagrams import _u_layer_views
from cubepath.fullsets import _u_layer_permutation, case_state
from cubepath.notation import pll_rows

# A design budget, not a correctness gate: Card 3's text slot is 33.4 mm and a
# cue that overran it would simply wrap, costing 1.21 mm of column — which the
# build's page-count gate already catches. The number is measured rather than
# guessed. Cues set in Libertinus 4.0pt average 0.5366 mm/char, and the widest
# real cue measures under 30 mm, ~89% of the slot. 56 keeps every cue on one
# line with the observed character mix. The first plan said 34, which would
# have forced hand-abbreviated cues for no reason at all.
CUE_MAX_CHARS = 56

# A case's corner story, canonicalised: the sorted `corner_facts` set.
CornerKey = tuple[tuple[str, str], ...]

# Which side strip of a plan-view diagram shows which face.
_STRIP = {"F": "bottom", "R": "right", "B": "top", "L": "left"}

# Where each strip's first sticker is drawn, and so what "the near end" and
# "the far end" of that strip mean to someone looking at the diagram. The top
# and bottom strips run left to right; the left and right strips run top to
# bottom, and the diagram's top is the back of the cube. Pinned by
# `test_strip_reading_order_matches_the_drawing` — invert one of these and
# every printed cue points at the wrong pair.
_ENDS = {
    "F": ("left", "right"),
    "B": ("left", "right"),
    "R": ("back", "front"),
    "L": ("back", "front"),
}
# Clockwise around the U layer, as the diagram is drawn.
_CLOCKWISE = ("top", "right", "bottom", "left")

BAR, LIGHTS, PAIR_L, PAIR_R = "bar", "lights", "pair-L", "pair-R"


def corner_facts(alg: str) -> frozenset[tuple[str, str]]:
    """(face, fact) for every side face of the state this algorithm solves.

    A face's U-layer row is three stickers. All three equal means that face is
    already solved (a bar); outer two equal means headlights; otherwise a
    matching adjacent pair sits on one side or neither.
    """
    _, sides = _u_layer_views(case_state(alg))
    facts = []
    for face, strip in _STRIP.items():
        a, b, c = sides[strip]
        if a == b == c:
            facts.append((face, BAR))
        elif a == c:
            facts.append((face, LIGHTS))
        elif a == b:
            facts.append((face, PAIR_L))
        elif b == c:
            facts.append((face, PAIR_R))
    return frozenset(facts)


def headlight_faces(facts: frozenset[tuple[str, str]]) -> set[str]:
    """Faces showing two matching corners. A solved face shows them too."""
    return {f for f, kind in facts if kind in (BAR, LIGHTS)}


_GROUP_BY_HEADLIGHTS = {
    4: "Edges Only",
    1: "Adjacent Corner Swap",
    0: "Diagonal Corner Swap",
}


def derived_group(alg: str) -> str:
    """Which corner case this is, from the headlight count alone.

    Four headlight faces means the corners are already home; exactly one means
    two corners swap across that face; none means the swap is diagonal. This
    reproduces JPerm's own `group` field for all 21 — see the test.
    """
    n = len(headlight_faces(corner_facts(alg)))
    if n not in _GROUP_BY_HEADLIGHTS:
        raise AssertionError(f"{n} headlight faces is not a legal PLL state")
    return _GROUP_BY_HEADLIGHTS[n]


def edge_cycles(alg: str) -> list[list[str]]:
    """The U-layer edge permutation, as cycles of strip names."""
    perm = _u_layer_permutation(case_state(alg))
    cycles, seen = [], set()
    for start in _CLOCKWISE:
        if start in seen or perm[start] == start:
            continue
        cycle, cur = [start], perm[start]
        while cur != start:
            cycle.append(cur)
            cur = perm[cur]
        seen.update(cycle)
        cycles.append(cycle)
    return cycles


def _turn(cycle: list[str]) -> str:
    """Which way a 3-cycle runs around the U layer.

    Read against the three *moving* positions in clockwise order, not against
    all four: one position is fixed, so a raw index step of 2 is a skip across
    the fixed one and says nothing about direction.
    """
    moving = [p for p in _CLOCKWISE if p in cycle]
    nxt = moving[(moving.index(cycle[0]) + 1) % 3]
    return "clockwise" if cycle[1] == nxt else "counter-clockwise"


def edge_phrase(alg: str) -> str:
    """How the edges move, in words. Only two pairs of cases need it."""
    cycles = edge_cycles(alg)
    if len(cycles) == 2 and all(len(c) == 2 for c in cycles):
        opposite = _CLOCKWISE.index(cycles[0][0]) - _CLOCKWISE.index(cycles[0][1])
        return "opposite edges swap" if opposite % 2 == 0 else "adjacent edges swap"
    if len(cycles) == 1 and len(cycles[0]) == 3:
        return f"3 edges {_turn(cycles[0])}"
    return ""


def signature(alg: str) -> tuple[CornerKey, str]:
    """The complete recognition state. Unique across all 21 PLL cases."""
    return (tuple(sorted(corner_facts(alg))), edge_phrase(alg))


@functools.cache
def _corner_collisions() -> set[CornerKey]:
    """Corner signatures shared by more than one case.

    Only these need the edge clause printed. Every other case is settled by
    its corners, and printing "3 edges clockwise" there would cost a third of
    the cue to say nothing.
    """
    counts: dict[CornerKey, int] = {}
    for row in pll_rows():
        key = tuple(sorted(corner_facts(row.alg)))
        counts[key] = counts.get(key, 0) + 1
    return {k for k, n in counts.items() if n > 1}


# ── Printed cue ───────────────────────────────────────────────────────
# A fixed template over derived facts. Faces are grouped by fact so the cue
# reads as one scan instruction rather than four separate observations.


def pair_end(face: str, kind: str) -> str:
    """Which end of that face's strip the matching pair sits at, in the words
    a reader can apply to the diagram in front of them."""
    return _ENDS[face][0 if kind == PAIR_L else 1]


def cue(alg: str) -> str:
    """The printed recognition cue: the whole signature, compactly.

    Closed-world by construction — everything true is named, so "and nothing
    else" is implied by the card's own instruction to read all four faces.
    """
    facts = corner_facts(alg)
    by_kind: dict[str, list[str]] = {}
    for face, kind in sorted(facts):
        by_kind.setdefault(kind, []).append(face)

    parts = []
    if by_kind.get(BAR):
        parts.append(f"{' '.join(by_kind[BAR])} solid")
    if lights := by_kind.get(LIGHTS):
        word = "headlights"
        parts.append(f"all 4 {word}" if len(lights) == 4 else f"{' '.join(lights)} {word}")
    pairs = [
        f"{face}-{pair_end(face, kind)}" for face, kind in sorted(facts) if kind in (PAIR_L, PAIR_R)
    ]
    if pairs:
        parts.append(f"pairs {' '.join(pairs)}")
    if tuple(sorted(facts)) in _corner_collisions() and (phrase := edge_phrase(alg)):
        parts.append(phrase)
    return "; ".join(parts) if parts else "nothing matches"


def pll_cues() -> dict[str, str]:
    """Case name -> printed cue, for every PLL the card prints."""
    return {r.name: cue(r.alg) for r in pll_rows()}


# ── Card 2: how many Sunes get you out ────────────────────────────────


_SUNE = ALGORITHMS["Sune"]
_AUF = ("", "U", "U2", "U'")


def sune_count(alg: str, limit: int = 6) -> int:
    """Fewest Sunes (with a free U before each) that orient the yellow face.

    This is what licenses the printed promise that repeating one algorithm
    always finishes the step — it is measured, not folklore.
    """
    start = state_before(alg)
    if start.u_face_solved():
        return 0
    seen = {tuple(map(tuple, start.faces.values()))}
    queue = deque([(start, 0)])
    while queue:
        cube, depth = queue.popleft()
        if depth >= limit:
            continue
        for auf in _AUF:
            nxt = cube.copy()
            if auf:
                nxt.apply(auf)
            nxt.apply(_SUNE)
            if nxt.u_face_solved():
                return depth + 1
            key = tuple(map(tuple, nxt.faces.values()))
            if key not in seen:
                seen.add(key)
                queue.append((nxt, depth + 1))
    raise AssertionError(f"no Sune sequence within {limit} orients {alg!r}")


OLL_CORNER_CASES = (
    "Sune",
    "Anti-Sune",
    "Pi",
    "Headlights",
    "Double Headlights",
    "Chameleon",
    "Bowtie",
)


def sune_fallbacks() -> dict[str, int]:
    """Case name -> the Sune count, for the seven corner-orientation cases."""
    return {c: sune_count(ALGORITHMS[c]) for c in OLL_CORNER_CASES}
