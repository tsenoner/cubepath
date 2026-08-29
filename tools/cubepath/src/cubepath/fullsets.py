"""Full OLL (57) + PLL (21) + F2L (41) case diagrams, derived from the app's
extracted dataset.

This is the boundary module: the app's JavaScript half verifies the algorithm
data and writes JSON, and this half reads that JSON and draws. Nothing is
retyped and no sticker is placed by hand — OLL/PLL derive from each case's
primary algorithm via the simulator (arrows from the real piece permutation),
F2L from each case's SpeedCubeDB setup.

Sources, all machine-verified where they are produced:
  jperm-raw.json — 57 OLL + 21 PLL, gated by app/tests/algs.spec.ts
  f2l-raw.json   — 41 F2L, gated by app/scripts/verify-f2l.mjs
"""

from __future__ import annotations

import functools
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cubepath.cube import COLORS, Cube, diagram_to_sim
from cubepath.diagrams import (
    _SIM_COLOR,
    UNREACHED,
    YELLOW,
    CubeDiagram,
    SlotDiagram,
    _colorize,
    _u_layer_views,
    _yellow_mask,
    dim,
    plan_view,
    render,
    render_slot,
)
from cubepath.notation import case_states, pll_algs

_REPO = Path(__file__).resolve().parents[4]
_DATA = _REPO / "app" / "src" / "data" / "extracted" / "jperm-raw.json"

# All 24 whole-cube orientations.
_ROTATIONS = [
    " ".join(t for t in (a, b) if t)
    for a in ("", "x", "x2", "x'", "z", "z'")
    for b in ("", "y", "y2", "y'")
]


@functools.cache
def _solved_case_state(alg: str) -> Cube:
    """The 24-rotation search, memoised. Never handed out directly — see
    `case_state`."""
    from cubepath.cube import invert_algorithm

    inv = invert_algorithm(alg)
    for rot in _ROTATIONS:
        c = Cube.solved()
        if rot:
            c.apply(rot)
        c.apply(inv)
        if all(c.faces[f][4] == COLORS[f] for f in COLORS):
            return c
    raise AssertionError(f"no pre-rotation brings centers home for {alg!r}")


def case_state(alg: str) -> Cube:
    """The state a (possibly net-rotating) algorithm solves, yellow up.

    For an alg A with net rotation, the case is A⁻¹ applied to a PRE-rotated
    solved cube (the rotation composes on the left of the inverse — applying
    it afterwards would conjugate the case onto the wrong face). Enumerate
    the 24 pre-rotations; exactly one lands every center home.

    The search is cached but the result is not: a `Cube` is mutable, so
    handing the cached instance to every caller means one `apply()` anywhere —
    an AUF probe, a recognition experiment — silently rewrites the case every
    later diagram and cue is derived from.
    """
    return _solved_case_state(alg).copy()


# Slugs for PLL case names ("Ja" -> "ja", "H" -> "h").
def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ── Piece-permutation → arrows (mirrors tests/test_derivation.py) ──────
# A piece is identified by the colours it shows: an edge by its one side
# colour, a corner by its two. That is all `_EDGE_HOME` and `_CORNER_HOME` say,
# and it is true on a cube of any order — a 4x4 dedge shows the same one colour
# a 3x3 edge does.
_EDGE_HOME = {"R": "bottom", "G": "right", "O": "top", "B": "left"}
# The same four corners as `_CORNER_STRIPS` below, addressed as 3x3 facelets
# instead of plan-view strip ends. Kept because tests/test_derivation.py
# classifies OCLL twists through it — an independent statement of the geometry
# the plan view encodes, which is worth having stated twice and gated once.
_CORNER_SIDES = {
    "tl": (("L", 0), ("B", 2)),
    "tr": (("B", 0), ("R", 2)),
    "br": (("R", 0), ("F", 2)),
    "bl": (("F", 0), ("L", 2)),
}
_CORNER_HOME = {
    frozenset({"R", "G"}): "br",
    frozenset({"R", "B"}): "bl",
    frozenset({"O", "G"}): "tr",
    frozenset({"O", "B"}): "tl",
}


# Which end of a plan-view side strip belongs to which corner. This is not a
# choice either: `plan_view` already put every strip in the order the picture
# reads, so the back-left corner is the first cell of the top strip and the
# first cell of the left strip, and so on around the ring. It holds for any n.
_CORNER_STRIPS = {
    "tl": (("top", 0), ("left", 0)),
    "tr": (("top", -1), ("right", 0)),
    "br": (("right", -1), ("bottom", -1)),
    "bl": (("bottom", 0), ("left", -1)),
}


def _plan_permutation(sides: dict[str, list[str]], n: int) -> dict[str, str]:
    """Anchor -> the anchor its current occupant belongs at, for any cube order.

    A piece is named by the colours it shows, never by where it sits, which is
    what makes this size-independent: an edge anchor is the n-2 middle cells of
    a strip (one sticker on a 3x3, a dedge's two wings on a 4x4) and they must
    all show one colour, or the "edge" is not a single piece and the diagram
    would be drawing an arrow for something that cannot move as a unit.
    """
    perm: dict[str, str] = {}
    for pos in ("top", "right", "bottom", "left"):
        shown = set(sides[pos][1 : n - 1])
        if len(shown) != 1:
            raise ValueError(f"{pos} edge is not a single piece: {sides[pos]}")
        perm[pos] = _EDGE_HOME[shown.pop()]
    for pos, ((s1, i1), (s2, i2)) in _CORNER_STRIPS.items():
        perm[pos] = _CORNER_HOME[frozenset({sides[s1][i1], sides[s2][i2]})]
    return perm


def _u_layer_permutation(cube: Cube) -> dict[str, str]:
    """The 3x3 case of `_plan_permutation`, read straight off the simulator."""
    return _plan_permutation(_u_layer_views(cube)[1], 3)


def _arrows_from_permutation(
    perm: dict[str, str],
) -> tuple[list[tuple[str, str]], list[list[str]]]:
    """Decompose the position->destination map into swaps and cycles."""
    swaps: list[tuple[str, str]] = []
    cycles: list[list[str]] = []
    seen: set[str] = set()
    for start in perm:
        if start in seen or perm[start] == start:
            continue
        cycle = [start]
        cur = perm[start]
        while cur != start:
            cycle.append(cur)
            cur = perm[cur]
        seen.update(cycle)
        if len(cycle) == 2:
            swaps.append((cycle[0], cycle[1]))
        else:
            cycles.append(cycle)
    return swaps, cycles


@functools.cache
def _load() -> dict[str, Any]:
    """The verified JPerm extraction, as parsed JSON (shape asserted by the
    app's own extractor, not re-declared here)."""
    data: dict[str, Any] = json.loads(_DATA.read_text())
    return data


def full_oll_cases() -> list[CubeDiagram]:
    """57 OLL diagrams: yellow/grey mask of the state each primary alg solves."""
    cases = []
    for c in _load()["oll"]:
        cube = case_state(c["algs"][0])
        u, sides = _u_layer_views(cube)
        cases.append(
            CubeDiagram(
                name=f"oll_{int(c['name']):02d}",
                label=f"OLL {c['name']} ({c['group']})",
                category="oll_full",
                u_face=_yellow_mask(u),
                top_side=_yellow_mask(sides["top"]),
                right_side=_yellow_mask(sides["right"]),
                bottom_side=_yellow_mask(sides["bottom"]),
                left_side=_yellow_mask(sides["left"]),
            )
        )
    return cases


def _pll_cases(prefix: str, alg_of: Callable[[dict[str, Any]], str]) -> list[CubeDiagram]:
    """21 PLL diagrams: true side colors + arrows derived from the permutation."""
    cases = []
    for c in _load()["pll"]:
        cube = case_state(alg_of(c))
        u, sides = _u_layer_views(cube)
        assert all(s == "Y" for s in u), f"PLL {c['name']}: U face not oriented"
        swaps, cycles = _arrows_from_permutation(_u_layer_permutation(cube))
        cases.append(
            CubeDiagram(
                name=f"{prefix}_{_slug(c['name'])}",
                label=f"{c['name']} Perm",
                category="pll_full",
                # OLL already oriented these nine; PLL must not disturb them.
                # See `_derived_pll_case` for why that is the dim tier.
                u_face=[dim(YELLOW)] * 9,
                top_side=_colorize(sides["top"]),
                right_side=_colorize(sides["right"]),
                bottom_side=_colorize(sides["bottom"]),
                left_side=_colorize(sides["left"]),
                swaps=swaps,
                cycles=cycles,
            )
        )
    return cases


def full_pll_cases() -> list[CubeDiagram]:
    """The 21 PLL diagrams as the guide needs them: JPerm's primary algorithm."""
    return _pll_cases("pll_full", lambda c: c["algs"][0])


def card_pll_cases() -> list[CubeDiagram]:
    """The 21 PLL diagrams as Card 3 needs them: derived from the algorithm
    the card actually prints, not JPerm's primary.

    Six of the 21 print the guide's algorithm instead, and three of those six
    solve a different state — the repo's Z-Perm and JPerm's differ by a `y`
    rotation. Rendering from `algs[0]` there would put a diagram beside an
    algorithm that does not solve it.
    """
    printed = pll_algs()
    return _pll_cases("pll_card", lambda c: printed[c["name"]])


def render_fullsets(output_dir: Path) -> int:
    count = 0
    for case in full_oll_cases() + full_pll_cases():
        render(case, output_dir)
        count += 1
    return count


# ── F2L (41 cases) ────────────────────────────────────────────────────
# Same contract as the OLL/PLL sets above: read the verified extraction, derive
# every sticker from the case's own algorithm through the simulator. What is
# different is that an F2L case is about *pieces in slots*, not about a mask on
# the U face, so the derivation has to name pieces — and naming a piece by a
# literal facelet index would be exactly the hand-written layout this repo
# refuses everywhere else.
#
# So nothing here is written down. A cube whose 54 "colours" are unique facelet
# ids (`_traced`) turns "where did this piece go" into a lookup, and the FR
# slot is found by intersecting the layers three moves disturb: the facelets a
# quarter turn of R, F and D all touch are exactly the three of the DFR corner,
# and the ones R and F touch while U and D do not are exactly the two of the FR
# edge. That falls out of `cube._MOVE_DEFS`, which the CLAUDE.md convention
# tests already gate, so the slot cannot drift from the simulator's geometry.

_F2L_DATA = _REPO / "app" / "src" / "data" / "extracted" / "f2l-raw.json"


@functools.cache
def _f2l_data() -> dict[str, Any]:
    """The verified F2L extraction, read once. `f2l_cases()` is called from the
    renderer and from several tests, and each call re-simulates all 41 setups;
    re-reading the file underneath them as well bought nothing."""
    data: dict[str, Any] = json.loads(_F2L_DATA.read_text())
    return data


# (face, index) over all 54 facelets, and the 27 the isometric view shows.
_ALL_FACELETS = [(f, i) for f in "UDFBRL" for i in range(9)]
_VISIBLE = [(f, a, b) for f in ("U", "F", "R") for a in range(3) for b in range(3)]


def _traced() -> Cube:
    """A cube whose stickers are unique facelet ids rather than colours.

    `Cube` only ever moves its sticker strings around, so feeding it labels
    instead of colours turns it into a piece tracker for free: after an
    algorithm, each position names the home facelet now sitting in it.
    """
    return Cube(faces={f: [f"{f}{i}" for i in range(9)] for f in "UDFBRL"})


@functools.cache
def _layer(move: str) -> frozenset[tuple[str, int]]:
    """The facelets one quarter turn of `move` disturbs."""
    before = _traced()
    after = _traced()
    after.apply(move)
    return frozenset(
        p for p in _ALL_FACELETS if after.faces[p[0]][p[1]] != before.faces[p[0]][p[1]]
    )


@functools.cache
def _fr_slot() -> tuple[frozenset[tuple[str, int]], frozenset[tuple[str, int]]]:
    """(corner facelets, edge facelets) of the front-right slot, derived."""
    corner = _layer("R") & _layer("F") & _layer("D")
    edge = (_layer("R") & _layer("F")) - _layer("D") - _layer("U")
    assert len(corner) == 3, f"FR slot corner is not a corner: {sorted(corner)}"
    assert len(edge) == 2, f"FR slot edge is not an edge: {sorted(edge)}"
    return corner, edge


def _sim_index(face: str, a: int, b: int) -> tuple[str, int]:
    """Isometric (face, a, b) -> the simulator's (face, flat index)."""
    sim_face, row, col = diagram_to_sim(face, a, b)
    return (sim_face, row * 3 + col)


def f2l_cases() -> list[SlotDiagram]:
    """The 41 F2L diagrams: the pair in true colour, the first two layers dim,
    the last layer grey, and the slot the pair belongs in outlined.

    The three tiers are decided by *provenance*, never by position:

    * **highlight** — a facelet whose piece is one of the two the FR slot wants
      home. Found by tracing where the slot's own facelets went, so it holds
      wherever the setup threw them.
    * **dim** — solved before this step and must survive it: outside the last
      layer, outside the slot, and not the pair. The setups only ever disturb
      the U layer and the FR slot, so this is the cross plus the three finished
      slots — asserted below rather than assumed.
    * **grey** — not reached yet: the last layer, plus whatever is currently
      squatting in the slot.
    """
    corner, edge = _fr_slot()
    slot_home = corner | edge
    slot_labels = {f"{f}{i}" for f, i in slot_home}
    u_layer = _layer("U")
    slot_visible = frozenset(v for v in _VISIBLE if _sim_index(*v) in slot_home)

    cases: list[SlotDiagram] = []
    for c in _f2l_data()["f2l"]:
        setup: str = c["setup"]
        cube = Cube.solved()
        cube.apply(setup)
        traced = _traced()
        traced.apply(setup)
        pair = {p for p in _ALL_FACELETS if traced.faces[p[0]][p[1]] in slot_labels}
        assert len(pair) == 5, f"F2L {c['number']}: pair is not a corner + an edge"

        colors: dict[tuple[str, int, int], str] = {}
        for v in _VISIBLE:
            face, idx = _sim_index(*v)
            sticker = cube.faces[face][idx]
            if (face, idx) in pair:
                colors[v] = _SIM_COLOR[sticker]
            elif (face, idx) in slot_home or (face, idx) in u_layer:
                colors[v] = UNREACHED
            else:
                assert sticker == COLORS[face], (
                    f"F2L {c['number']}: {v} is dimmed as already solved but holds {sticker}"
                )
                colors[v] = dim(_SIM_COLOR[sticker])

        cases.append(
            SlotDiagram(
                name=f"f2l_{int(c['number']):02d}",
                label=f"F2L {c['number']} ({c['group']})",
                subdir="f2l",
                colors=colors,
                slot=slot_visible,
            )
        )
    return cases


def render_f2l(output_dir: Path) -> int:
    count = 0
    for case in f2l_cases():
        render_slot(case, output_dir)
        count += 1
    return count


# ── The 4x4 sets: 27 OLL + 22 PLL ─────────────────────────────────────
# THE ARCHITECTURE, stated where the code that depends on it lives.
#
# `cube.py` is a 3x3x3 mirror and is gated to stay one — it refuses big-cube
# notation rather than returning a confident wrong state, which is what it used
# to do. So the state of a 4x4 case does not come from Python at all. It comes
# from the cubing.js kpuzzle, through `app/scripts/gen-case-states.mjs`, which
# writes `case-states.json`; this module reads it and draws. JavaScript is the
# single source of cube truth, Python owns the rendering, and the JSON is the
# seam — the same shape as `jperm-raw.json`, generalised from algorithms to
# states.
#
# What that buys, concretely: the 49 diagrams below are derived from a model
# that `tests/test_case_states.py` compares against cube.py facelet-for-facelet
# on all 119 cases where both can speak. Nothing here is hand-placed, and the
# rule against writing a 4x4 simulator in Python is not a matter of taste — a
# second cube model is how you get two plausible pictures and no way to tell
# which is right.
#
# THE VIEW is the last-layer plan view the 57 OLL and 21 PLL diagrams already
# use, one cell wider. That is not a compromise; it is what every 4x4 reference
# draws, and it is the only view in which OLL parity is legible: a flipped
# dedge shows as one wing yellow on top and its partner yellow on the side,
# which no three-cell row can express.
#
# THE STICKERING follows the 3x3 sets exactly, and it is not the same answer
# for OLL as for PLL, because they do not stand in the same place in the
# method. An OLL diagram has NO earlier-solved region in frame: the U face is
# the thing being oriented and the mask on it means "not yellow yet", so two
# tiers is the whole truth and the 4x4 OLL set stays two-tier. A PLL diagram
# does: OLL has already oriented all of the U face, and PLL must hand it back
# untouched. That is the dim tier by definition, so the U face of every PLL
# plan view — 3x3 and 4x4 alike — is drawn `dim(YELLOW)` and the side bands,
# which are the only thing PLL permutes, keep full colour. A 4x4 set that
# differed here would read as a different family of picture rather than the
# same one at another size.
#
# THE AUF is not normalised, exactly as in the 3x3 sets. Each diagram is the
# state its own printed algorithm solves, whatever rotation that algorithm
# leaves the top layer in. JPerm's group names ("Edges Only", "Adjacent Corner
# Swap") name the case up to AUF, so a picture may show corner arrows in an
# "Edges Only" case — 7 of the 21 shipped 3x3 PLL diagrams already do, Z-perm
# among them. Re-orienting the picture to match the label would break the one
# property worth more than a tidy label: apply the algorithm beside it to the
# state drawn, and the cube is solved. `tests/test_diagrams.py` gates the label
# the honest way, up to AUF.

# The case-states loader lives in `notation`, which owns the JS->Python data
# boundary; this module reads the same file through it rather than opening it a
# second time.


@functools.cache
def _color_of_face() -> dict[str, str]:
    """JSON face letter -> the simulator's colour letter.

    The two halves of this repo name the same six faces in different
    vocabularies: the JSON says which FACE a sticker shows, because cubing.js
    hard-codes a palette this project does not use, and the drawing code says
    which COLOUR. This function is the only place they meet, and it checks
    rather than assumes: the JSON's own `faceColors` must agree with cube.py's
    scheme on every face, so a palette change on either side fails here instead
    of silently repainting 49 diagrams.
    """
    named = case_states()["faceColors"]
    for face, letter in COLORS.items():
        name = named[face]
        if not name.startswith(letter):
            raise AssertionError(
                f"case-states.json calls {face} {name}, cube.py calls it {letter!r}"
            )
    return dict(COLORS)


def _states_of(set_name: str) -> list[dict[str, Any]]:
    cases = [c for c in case_states()["cases"] if c["set"] == set_name]
    if not cases:
        raise AssertionError(f"case-states.json carries no {set_name} cases")
    return cases


def _case_order(case: dict[str, Any]) -> int:
    """The cube order this case is on, read from the layout it belongs to."""
    n: int = case_states()["layouts"][case["puzzle"]]["n"]
    return n


def _case_plan_view(case: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    """The case's U layer as the plan view needs it, in colour letters."""
    of = _color_of_face()
    faces = {face: [of[ch] for ch in row] for face, row in case["state"].items()}
    return plan_view(faces, _case_order(case))


def diagram_name(case_id: str) -> str:
    """Case id -> diagram filename stem.

    Shared with `app/scripts/gen-cases.mjs`, which builds the same string to
    point each case at its icon. Two implementations that must agree, so
    `tests/test_diagrams.py` asserts every icon the app emits resolves to a
    file this generator actually wrote.
    """
    return case_id.replace(".", "_").replace("-", "_")


def plan_oll_cases(set_name: str, category: str) -> list[CubeDiagram]:
    """OLL diagrams for a whole set, straight from the exported states: yellow
    where the last layer is already oriented, grey where it is not.

    Parameterised by set rather than fixed to the 4x4 one so the SAME code can
    be pointed at the 3x3 OLL set, where cube.py can derive the answer
    independently — `tests/test_diagrams.py` does exactly that, and a
    disagreement between the two cube models fails the build. A renderer that
    only ever ran on states nothing could check would be untestable by
    construction.
    """
    cases = []
    for case in _states_of(set_name):
        u, sides = _case_plan_view(case)
        cases.append(
            CubeDiagram(
                name=diagram_name(case["id"]),
                label=f"{case['name']} — {case['group']}",
                category=category,
                n=_case_order(case),
                u_face=_yellow_mask(u),
                top_side=_yellow_mask(sides["top"]),
                right_side=_yellow_mask(sides["right"]),
                bottom_side=_yellow_mask(sides["bottom"]),
                left_side=_yellow_mask(sides["left"]),
            )
        )
    return cases


def plan_pll_cases(set_name: str, category: str) -> list[CubeDiagram]:
    """PLL diagrams for a whole set: true side colours, and arrows read off the
    real piece permutation — never declared, at either cube size. Parameterised
    for the same reason `plan_oll_cases` is."""
    cases = []
    for case in _states_of(set_name):
        n = _case_order(case)
        u, sides = _case_plan_view(case)
        assert all(s == "Y" for s in u), f"{case['id']}: U face not oriented"
        swaps, cycles = _arrows_from_permutation(_plan_permutation(sides, n))
        cases.append(
            CubeDiagram(
                name=diagram_name(case["id"]),
                label=f"{case['name']} — {case['group']}",
                category=category,
                n=n,
                u_face=[dim(YELLOW)] * (n * n),
                top_side=_colorize(sides["top"]),
                right_side=_colorize(sides["right"]),
                bottom_side=_colorize(sides["bottom"]),
                left_side=_colorize(sides["left"]),
                swaps=swaps,
                cycles=cycles,
            )
        )
    return cases


def big_oll_cases() -> list[CubeDiagram]:
    """The 27 4x4 OLL diagrams."""
    return plan_oll_cases("4x4oll", "444_oll")


def big_pll_cases() -> list[CubeDiagram]:
    """The 22 4x4 PLL diagrams."""
    return plan_pll_cases("4x4pll", "444_pll")


def render_big_sets(output_dir: Path) -> int:
    count = 0
    for case in big_oll_cases() + big_pll_cases():
        render(case, output_dir)
        count += 1
    return count
