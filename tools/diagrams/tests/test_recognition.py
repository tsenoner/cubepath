"""Derived recognition: the facts a learner reads, checked against the cube.

The point of this file is that Card 3's recognition wording is *generated*.
If these pass, no cue on the card was written from memory.
"""

from __future__ import annotations

import json

import pytest

from cubepath.notation import _JPERM, pll_rows
from cubepath.recognition import (
    _ENDS,
    CUE_MAX_CHARS,
    OLL_CORNER_CASES,
    corner_facts,
    cue,
    derived_group,
    edge_cycles,
    headlight_faces,
    pll_cues,
    signature,
    sune_count,
    sune_fallbacks,
)

_ROWS = list(pll_rows())


# ── The load-bearing claim ────────────────────────────────────────────


@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.name)
def test_derived_group_matches_jperm(row) -> None:
    """Counting headlight faces reproduces JPerm's own classification.

    This is what makes the cues trustworthy: an independent derivation from
    the cube state agrees with the published dataset on every case, including
    the three where the card prints the guide's algorithm instead of JPerm's.
    """
    assert derived_group(row.alg) == row.group


def test_headlight_counts_are_the_three_legal_values() -> None:
    counts = sorted(len(headlight_faces(corner_facts(r.alg))) for r in _ROWS)
    assert set(counts) == {0, 1, 4}
    assert counts.count(4) == 4, "four cases have their corners already home"
    assert counts.count(1) == 12, "twelve adjacent-swap cases"
    assert counts.count(0) == 5, "five diagonal-swap cases"


def test_group_counts_match_the_dataset() -> None:
    raw = json.loads(_JPERM.read_text())["pll"]
    from collections import Counter

    assert Counter(derived_group(r.alg) for r in _ROWS) == Counter(c["group"] for c in raw)


# ── Cues ──────────────────────────────────────────────────────────────


def test_every_case_has_a_unique_signature() -> None:
    """Recognition works at all only if no two cases look identical."""
    sigs = {r.name: signature(r.alg) for r in _ROWS}
    assert len(set(sigs.values())) == 21, "two PLL cases are indistinguishable"


def test_cues_are_unique() -> None:
    cues = pll_cues()
    assert len(set(cues.values())) == 21, "two cases print the same cue"


@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.name)
def test_cue_fits_the_card(row) -> None:
    assert len(cue(row.alg)) <= CUE_MAX_CHARS, cue(row.alg)


def test_only_the_colliding_pairs_mention_edges() -> None:
    """Corners settle 17 of the 21. Printing an edge clause on those would
    spend a third of the cue saying nothing."""
    with_edges = {r.name for r in _ROWS if "edges" in cue(r.alg)}
    assert with_edges == {"H", "Z", "Ua", "Ub"}


def test_the_two_collisions_are_separated_by_direction() -> None:
    cues = pll_cues()
    assert cues["H"] != cues["Z"]
    assert cues["Ua"] != cues["Ub"]
    # Ua and Ub are the same 3-cycle run the other way round — if the turn
    # derivation regresses, both read "clockwise" and the card is wrong.
    assert "counter-clockwise" in cues["Ua"] and "counter" not in cues["Ub"]


@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r.name)
def test_edge_permutation_is_a_legal_pll(row) -> None:
    """Every PLL moves the U layer only, in cycles that compose to an even
    permutation together with the corners."""
    cycles = edge_cycles(row.alg)
    moved = sorted(p for c in cycles for p in c)
    assert len(moved) == len(set(moved)), f"{row.name}: overlapping edge cycles"
    assert all(len(c) in (2, 3, 4) for c in cycles), cycles


# ── Card 2's promise: repeating one algorithm always finishes the step ─


def test_sune_counts_are_derived_not_claimed() -> None:
    counts = {f.case: f.sunes for f in sune_fallbacks()}
    assert counts == {
        "Sune": 1,
        "Anti-Sune": 2,
        "Pi": 2,
        "Headlights": 3,
        "Double Headlights": 2,
        "Chameleon": 3,
        "Bowtie": 3,
    }
    assert max(counts.values()) == 3, "the printed 'at most three Sunes' is measured"
    assert set(counts) == set(OLL_CORNER_CASES)


def test_solved_needs_no_sune() -> None:
    assert sune_count("") == 0


def test_niklas_wrecks_the_yellow_face() -> None:
    """The card says Niklas moves corners but ruins the yellow face, which is
    why it is retired once the yellow face is solved first. That is the
    simulator's answer, not an opinion."""
    from cubepath.algs import ALGORITHMS
    from cubepath.cube import Cube
    from cubepath.recognition import _u_face_solved

    cube = Cube.solved()
    cube.apply(ALGORITHMS["Niklas"])
    assert not _u_face_solved(cube)


# ── The geometry the cue wording rests on ─────────────────────────────


def test_strip_reading_order_matches_the_drawing(tmp_path) -> None:
    """`_ENDS` claims the top and bottom strips run left-to-right and the side
    strips run top-to-bottom. Every printed cue points at a pair using those
    words, so if the renderer ever draws a strip the other way round, the card
    sends the reader to the wrong end of the wrong face. Read it off the SVG.
    """
    import re

    from cubepath.diagrams import YELLOW, CubeDiagram, render
    from cubepath.recognition import _ENDS, _STRIP

    # One unique colour per (strip, index) so every rect is identifiable; a
    # shared palette cannot separate strips, since a whole strip shares an axis.
    def mark(strip: int, i: int) -> str:
        return f"#{10 * strip + i:02d}{10 * strip + i:02d}{10 * strip + i:02d}"

    case = CubeDiagram(
        name="reading_order",
        label="reading order probe",
        category="pll_edges",
        u_face=[YELLOW] * 9,
        top_side=[mark(1, i) for i in range(3)],
        right_side=[mark(2, i) for i in range(3)],
        bottom_side=[mark(3, i) for i in range(3)],
        left_side=[mark(4, i) for i in range(3)],
    )
    svg = render(case, tmp_path).read_text()

    def pos(color: str) -> tuple[float, float]:
        m = re.search(rf'fill="{color}"[^/]*?x="([\d.]+)" y="([\d.]+)"', svg)
        assert m, f"probe colour {color} never reached the SVG"
        return float(m.group(1)), float(m.group(2))

    # Horizontal strips (top = back, bottom = front): index 0 is leftmost.
    for strip, name in ((1, "top"), (3, "bottom")):
        xs = [pos(mark(strip, i))[0] for i in range(3)]
        assert xs == sorted(xs), f"{name} strip is drawn right-to-left: {xs}"
    # Vertical strips (right, left): index 0 is topmost, i.e. nearest the back.
    for strip, name in ((2, "right"), (4, "left")):
        ys = [pos(mark(strip, i))[1] for i in range(3)]
        assert ys == sorted(ys), f"{name} strip is drawn bottom-to-top: {ys}"

    # And the words follow from that: the diagram's top edge is the cube's back.
    assert _ENDS["F"] == _ENDS["B"] == ("left", "right")
    assert _ENDS["R"] == _ENDS["L"] == ("back", "front")
    assert set(_STRIP) == set(_ENDS)


def test_every_pair_names_a_face_and_an_end() -> None:
    """A pair clause without its face is ambiguous: two strips meet at every
    diagram corner, and three cases carry two pairs at the same corner."""
    import re

    for row in _ROWS:
        for token in re.findall(r"\b([FRBL])-(\w+)", cue(row.alg)):
            face, end = token
            assert end in _ENDS[face], f"{row.name}: {face}-{end} is not an end of {face}"
