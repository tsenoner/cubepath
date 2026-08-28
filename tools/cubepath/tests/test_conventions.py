"""CLAUDE.md's cube conventions, checked against the simulator.

CLAUDE.md is the file every future session reads before touching a diagram, and
everything in this repo is derived from the conventions it states. That made it
the one document where a wrong sentence was both maximally damaging and entirely
unchecked: it described `R` as `top->front->bottom->back` and `U` as
`front->right->back->left` — which are `R'` and `U'` — and listed the "CW from
top" adjacency counter-clockwise. Nothing caught it, because prose does not run.

So these tests *parse CLAUDE.md* rather than restating its claims. Restating them
would recreate the problem one level down: two copies of the same fact, drifting.
Here the document is the input, `cube.py` is the oracle, and editing either one
into disagreement fails the build.

Every parser below raises when its pattern goes missing. That is deliberate — a
reformat that quietly stopped matching would silently switch the gate off, which
is worse than no gate at all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cubepath import cube as cube_module
from cubepath.cube import SIZE, Cube, UnsupportedPuzzleError

CLAUDE_MD = Path(__file__).resolve().parents[3] / "CLAUDE.md"

# Colour words CLAUDE.md uses -> the simulator's one-letter codes. "Blue" and
# "Back" both start with B, so names are mapped explicitly rather than sliced.
COLOR_LETTER = {
    "Yellow": "Y",
    "White": "W",
    "Red": "R",
    "Orange": "O",
    "Green": "G",
    "Blue": "B",
}


@pytest.fixture(scope="module")
def doc() -> str:
    assert CLAUDE_MD.is_file(), f"{CLAUDE_MD} is missing — these gates guard that file"
    return CLAUDE_MD.read_text()


# ── The oracle ────────────────────────────────────────────────────────


def face_flow(move: str) -> dict[str, str]:
    """Which face each face's stickers move to, derived by turning a solved cube.

    A quarter turn carries exactly three stickers of one face's colour onto the
    next face in the cycle, so "the face that ends up holding exactly 3 of this
    colour" identifies the destination without hardcoding which row or column
    the move happens to take. The turning face itself keeps all 9 and drops out.
    """
    solved, turned = Cube.solved(), Cube.solved()
    turned.apply(move)
    flow = {}
    for src in "UDFBLR":
        color = solved.faces[src][4]  # the centre never moves, so it names the face
        landed = [d for d in "UDFBLR" if sum(1 for s in turned.faces[d] if s == color) == 3]
        if len(landed) == 1:
            flow[src] = landed[0]
    return flow


def cycle_to_flow(cycle: list[str]) -> dict[str, str]:
    """['F','U','B','D','F'] -> {'F':'U','U':'B','B':'D','D':'F'}."""
    return {a: b for a, b in zip(cycle[:-1], cycle[1:], strict=True)}


# ── Colour scheme ─────────────────────────────────────────────────────


def _face_table(doc: str) -> list[tuple[str, str, str, str]]:
    rows = re.findall(
        r"^\|\s*([UDFBLR]) \([A-Za-z]+\)\s*\|[^|]*\|\s*\**([A-Za-z]+)\**\s*\|"
        r"\s*\**([A-Za-z]+)\**\s*\(([UDFBLR])\)\s*\|",
        doc,
        re.M,
    )
    assert len(rows) == 6, (
        f"expected 6 face rows in CLAUDE.md's colour table, parsed {len(rows)} — "
        "the table format changed and this gate stopped reading it"
    )
    return rows


def test_face_colors_match_the_simulator(doc) -> None:
    """The Face/Colour column is the scheme every diagram is derived from."""
    solved = Cube.solved()
    for face, color, _, _ in _face_table(doc):
        want = COLOR_LETTER[color]
        assert solved.faces[face][4] == want, (
            f"CLAUDE.md says {face} is {color} ({want}); the simulator has {solved.faces[face][4]}"
        )


def test_opposite_faces_match_the_simulator(doc) -> None:
    """A face's opposite must be the face carrying the opposite colour."""
    solved = Cube.solved()
    for face, _, opp_color, opp_face in _face_table(doc):
        assert solved.faces[opp_face][4] == COLOR_LETTER[opp_color], (
            f"CLAUDE.md pairs {face} with {opp_color} ({opp_face}), but {opp_face} is "
            f"{solved.faces[opp_face][4]}"
        )
        assert opp_face != face


# ── Adjacency ─────────────────────────────────────────────────────────


def test_adjacency_ring_is_really_clockwise_from_the_top(doc) -> None:
    """The claim that bit us: the ring was listed counter-clockwise.

    "CW from top" is exactly the direction a U turn carries stickers, so the
    named order must match the flow a U turn actually produces.
    """
    m = re.search(r"\*\*Adjacency \(CW from top\):\*\*\s*([A-Za-z\s→]+?)\.", doc)
    assert m, "could not find the Adjacency line in CLAUDE.md — gate is not reading anything"
    names = [n.strip() for n in m.group(1).split("→")]
    assert len(names) == 5 and names[0] == names[-1], f"ring should close on itself, got {names}"

    by_color = {Cube.solved().faces[f][4]: f for f in "UDFBLR"}
    ring = [by_color[COLOR_LETTER[n]] for n in names]
    assert cycle_to_flow(ring) == face_flow("U"), (
        f"CLAUDE.md's ring {' → '.join(names)} maps to {ring[:-1]}, but a U turn moves "
        f"{face_flow('U')} — the listed order is the reverse (that is counter-clockwise)"
    )


# ── Move directions ───────────────────────────────────────────────────


def _move_bullets(doc: str) -> dict[str, list[str]]:
    found = re.findall(
        r"^- ([RUF]) CW from [+-][xyz]:[^(\n]*\(([UDFBLR](?:→[UDFBLR])+)\)", doc, re.M
    )
    assert len(found) == 3, (
        f"expected 3 'X CW from ...' bullets each carrying a (F→U→B→D→F) style face "
        f"cycle, parsed {len(found)} — add the cycle in parentheses or this gate is blind"
    )
    return {move: cycle.split("→") for move, cycle in found}


@pytest.mark.parametrize("move", ["R", "U", "F"])
def test_documented_turn_direction_is_the_real_one(doc, move) -> None:
    """The documented face cycle must be the turn, not its inverse.

    This distinguishes X from X': under R the U face goes to B, under R' it goes
    to F, so an inverted description cannot pass.
    """
    cycle = _move_bullets(doc)[move]
    assert cycle[0] == cycle[-1], f"{move}'s cycle should close on itself, got {cycle}"
    documented = cycle_to_flow(cycle)
    actual = face_flow(move)
    assert documented == actual, (
        f"CLAUDE.md documents {move} as {'→'.join(cycle)}, but the simulator gives "
        f"{actual}. If they are exact reverses, the doc is describing {move}'."
    )
    # and prove the gate is sharp: the inverse must NOT satisfy it
    assert documented != face_flow(f"{move}'"), f"{move} and {move}' are indistinguishable here"


def test_slice_moves_follow_the_faces_they_claim_to(doc) -> None:
    """ "M follows L direction, S follows F direction, E follows D direction."

    Each slice must move faces exactly as its named face turn does — the sign
    convention for M in particular is a classic place to be off by an inverse.
    """
    pairs = re.findall(r"([MSE]) follows ([UDFBLR]) direction", doc)
    assert len(pairs) == 3, (
        f"expected 3 'slice follows face' claims in CLAUDE.md, parsed {len(pairs)}"
    )
    for slice_move, face in pairs:
        assert face_flow(slice_move) == face_flow(face), (
            f"CLAUDE.md says {slice_move} follows {face}, but {slice_move} moves "
            f"{face_flow(slice_move)} while {face} moves {face_flow(face)}"
        )


# ── U-face index convention ───────────────────────────────────────────


def test_u_face_index_convention_matches_the_simulator(doc) -> None:
    """ "Top row = back of cube, bottom row = front" — the sentence every plan-view
    diagram's sticker order depends on."""
    assert re.search(
        r"U-face indices are row-major.*?Top row = back of cube, bottom row = front",
        doc,
        re.S,
    ), "the U-face index convention sentence changed — this gate stopped reading it"

    # Turn the back layer only; the U face's back row (indices 0..2) must change
    # and its front row (6..8) must not.
    before = Cube.solved()
    after = Cube.solved()
    after.apply("B")
    top_row_moved = [before.faces["U"][i] != after.faces["U"][i] for i in (0, 1, 2)]
    bottom_row_moved = [before.faces["U"][i] != after.faces["U"][i] for i in (6, 7, 8)]
    assert all(top_row_moved), "U indices 0-2 should be the BACK row; a B turn did not change them"
    assert not any(bottom_row_moved), "U indices 6-8 should be the FRONT row; a B turn changed them"


# ── Scope: cube.py is a 3x3 mirror, and both documents say so ─────────
#
# The judged architecture ruling is that cube.py stays a 3x3-only mirror and
# the cubing.js kpuzzle is the source of truth for anything larger. A ruling
# that lives only in prose is a ruling that gets forgotten, so it is checked
# the same way every other convention in this file is: the documents are the
# input, the simulator is the oracle, and widening one without the other fails
# the build.


def test_claude_md_still_describes_a_3x3_state_shape(doc) -> None:
    """CLAUDE.md pins the simulator's state as "6 faces x 9 stickers". If
    someone ever parameterises cube.py by cube size, that sentence silently
    becomes false — so assert it against the real object instead."""
    m = re.search(r"State: (\d+) faces × (\d+) stickers", doc)
    assert m, "CLAUDE.md's 'State: 6 faces × 9 stickers' sentence changed — this gate is blind"
    faces, stickers = int(m.group(1)), int(m.group(2))

    solved = Cube.solved()
    assert len(solved.faces) == faces, (
        f"CLAUDE.md says {faces} faces; the simulator has {len(solved.faces)}"
    )
    for name, face in solved.faces.items():
        assert len(face) == stickers, (
            f"CLAUDE.md says {stickers} stickers per face; {name} has {len(face)}"
        )


def test_cube_py_declares_its_own_scope_and_names_the_real_source_of_truth() -> None:
    """The docstring is where the next reader looks before adding a move table.
    It has to tell them not to, and where to go instead."""
    text = cube_module.__doc__ or ""
    assert "3×3×3" in text, "cube.py's docstring no longer states that it models a 3x3 only"
    assert "kpuzzle" in text and "cubing.js" in text, (
        "cube.py's docstring must name the cubing.js kpuzzle as the source of truth "
        "for anything larger than a 3x3 — otherwise the next session writes a 4x4 "
        "simulator here, which is the duplicated-cube-model mistake made twice"
    )
    assert "4×4" in text and "5×5" in text, (
        "the docstring must say out loud which puzzles do NOT belong in this file"
    )


def test_the_simulator_really_is_3x3_shaped() -> None:
    """The oracle half of the docstring's claim. Every layer count in cube.py is
    a literal 3; if that ever stops being true the docstring above is a lie and
    this fails before anyone can derive a diagram from it."""
    assert SIZE == 3
    labels = [str(i) for i in range(SIZE * SIZE)]
    assert sorted(cube_module._rotate_face_cw(labels)) == sorted(labels), (
        f"a face rotation must permute exactly {SIZE * SIZE} stickers"
    )
    for move, (_, strips) in cube_module._MOVE_DEFS.items():
        assert len(strips) == 4, f"{move} should cycle 4 strips"
        for strip in strips:
            assert len(strip) == SIZE, f"{move} has a strip of {len(strip)} on a {SIZE}x{SIZE}"


def test_a_declared_big_cube_is_refused_rather_than_answered() -> None:
    """The concrete promise the docstring makes: ask this module a 4x4 question
    and it declines, instead of returning a plausible 3x3 answer."""
    with pytest.raises(UnsupportedPuzzleError):
        Cube.solved(size=4)
