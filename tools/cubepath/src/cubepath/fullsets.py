"""Full OLL (57) + PLL (21) case diagrams, derived from the extracted dataset.

Reads app/src/data/extracted/jperm-raw.json (algs machine-verified at
extraction time) and derives every diagram from its primary algorithm via the
simulator — the same no-hand-drawn-stickers rule as the core sets. PLL arrows
are computed from the actual piece permutation.
"""

from __future__ import annotations

import functools
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cubepath.cube import Cube
from cubepath.diagrams import (
    YELLOW,
    CubeDiagram,
    _colorize,
    _u_layer_views,
    _yellow_mask,
    render,
)
from cubepath.notation import pll_algs

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
    from cubepath.cube import COLORS, invert_algorithm

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
_EDGE_STICKER = {"top": ("B", 1), "right": ("R", 1), "bottom": ("F", 1), "left": ("L", 1)}
_EDGE_HOME = {"R": "bottom", "G": "right", "O": "top", "B": "left"}
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


def _u_layer_permutation(cube: Cube) -> dict[str, str]:
    perm: dict[str, str] = {}
    for pos, (face, idx) in _EDGE_STICKER.items():
        perm[pos] = _EDGE_HOME[cube.faces[face][idx]]
    for pos, ((f1, i1), (f2, i2)) in _CORNER_SIDES.items():
        perm[pos] = _CORNER_HOME[frozenset({cube.faces[f1][i1], cube.faces[f2][i2]})]
    return perm


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
                u_face=[YELLOW] * 9,
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
