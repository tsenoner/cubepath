"""Diagram ↔ algorithm consistency tests.

These tests close the F4 blind spot: every published diagram is derived from
its algorithm's pre-state, arrows must match the actual piece permutation,
and the guide's tables must match the canonical algorithm data.
"""

import functools
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from cubepath.algs import ALGORITHMS
from cubepath.cube import (
    COLORS,
    Cube,
    UnsupportedNotationError,
    diagram_to_sim,
    parse_algorithm,
    state_before,
)
from cubepath.diagrams import (
    _SIM_COLOR,
    UNORIENTED,
    UNREACHED,
    YELLOW,
    _align_edge_cases,
    _corner_case_steps,
    _corner_pos_case,
    _edge_case_steps,
    _oll_corner_cases,
    _oll_cross_cases,
    _orient_corner_case,
    _orient_corner_cases_15,
    _pll_corner_cases,
    _pll_edge_cases,
    _step_cases,
    _step_sticker_color,
    _u_layer_views,
    dim,
)

# The generator owns the U-layer sticker map; importing it (rather than keeping
# a second copy here) is what stops the two from drifting apart silently.
from cubepath.fullsets import (
    _ALL_FACELETS,
    _CORNER_SIDES,
    _ROTATIONS,
    _fr_slot,
    _layer,
    _traced,
    _u_layer_permutation,
    f2l_cases,
)
from cubepath.recognition import OLL_CORNER_CASES as _OCLL_ALGS

GUIDE = Path(__file__).resolve().parents[3] / "guide" / "cubepath.md"
_APP_DATA = Path(__file__).resolve().parents[3] / "app" / "src" / "data" / "extracted"

# ── Frame anchors ────────────────────────────────────────────────────
# Freeze the plan-view conventions (U row 0 = back; side strips as viewed
# from above, front at bottom) with two asymmetric hand-checked cases.


M = UNORIENTED  # the OLL orientation mask, spelled short for the anchor rows


def _case(cases, name):
    return next(c for c in cases if c.name == name)


def test_sune_anchor():
    sune = _case(_oll_corner_cases(), "oll_sune")
    assert sune.u_face == [M, YELLOW, M, YELLOW, YELLOW, YELLOW, YELLOW, YELLOW, M]
    assert sune.top_side == [YELLOW, M, M]
    assert sune.right_side == [YELLOW, M, M]
    assert sune.bottom_side == [M, M, YELLOW]
    assert sune.left_side == [M, M, M]


def test_antisune_anchor():
    a = _case(_oll_corner_cases(), "oll_antisune")
    assert a.u_face == [M, YELLOW, YELLOW, YELLOW, YELLOW, YELLOW, M, YELLOW, M]
    assert a.top_side == [M, M, M]
    assert a.right_side == [M, M, YELLOW]
    assert a.bottom_side == [YELLOW, M, M]
    assert a.left_side == [YELLOW, M, M]


def test_hook_is_phase1_angle():
    """Hook diagram shows the L in back-left — the angle where F-sexy-F' → Line."""
    hook = _case(_oll_cross_cases(), "oll_hook")
    assert hook.u_face[1] == YELLOW and hook.u_face[3] == YELLOW  # back + left edges
    assert hook.u_face[5] == M and hook.u_face[7] == M


def test_hook_wide_is_phase15_angle():
    """`oll_hook_wide` shows the L in front-right — the angle f-sexy-f' solves.

    It is `eo.hook`'s /reference icon, the guide's Phase 1.5 figure and Card 2's
    picture, and its twin `oll_hook` is the Phase 1 hold. The pair is the whole
    recognition cue and nothing but the file name tells them apart, which is
    exactly how a back-left picture shipped beside a front-right cue. The two
    are one case at opposite holds, so each must be the other's 180° turn — a
    plan view rotated a half turn is its own row-major reversal.
    """
    wide = _case(_oll_cross_cases(), "oll_hook_wide")
    assert wide.u_face[5] == YELLOW and wide.u_face[7] == YELLOW  # right + front edges
    assert wide.u_face[1] == M and wide.u_face[3] == M
    narrow = _case(_oll_cross_cases(), "oll_hook")
    assert wide.u_face == list(reversed(narrow.u_face))


def test_phase1_cross_chain():
    """The Phase-1 flow Dot →(F-sexy-F')→ Hook →(F-sexy-F')→ Line → solved works
    when the learner holds Hook at back-left and Line horizontal, as pictured.

    The Hook state here is the PICTURE's own — `state_before` of two narrow
    passes, which is what `_oll_cross_cases()` draws `oll_hook` from. It was
    hand-built as the wide-f pre-state turned `y2`: a different cube state that
    only happens to share the U-face edge pattern, so once the generator stopped
    rotating, the test was checking a state no diagram is derived from.
    """
    f_alg = ALGORITHMS["F-sexy-F'"]
    # Hook held with L in back-left → Line (horizontal)
    c = state_before(f"{f_alg} {f_alg}")
    c.apply(f_alg)
    u = c.faces["U"]
    assert u[3] == "Y" and u[5] == "Y" and u[1] != "Y" and u[7] != "Y"
    # Line horizontal → cross solved
    c2 = state_before(f_alg)
    c2.apply(f_alg)
    assert c2.u_cross_solved()


# ── OCLL coverage (F1 regression guard) ──────────────────────────────
# The seven corner-orientation algorithms must cover all seven OCLL twist
# classes exactly once — no gaps (like the old missing H), no duplicates.

_CORNER_UP = {"tl": 0, "tr": 2, "br": 8, "bl": 6}
_RING = ["tl", "tr", "br", "bl"]


def _ocll_class(cube: Cube) -> str:
    """Canonical corner-twist pattern, invariant under U-layer view rotation."""
    pattern = []
    for pos in _RING:
        if cube.faces["U"][_CORNER_UP[pos]] == "Y":
            pattern.append("U")
        else:
            (pf, pi), (ff, fi) = _CORNER_SIDES[pos]
            if cube.faces[pf][pi] == "Y":
                pattern.append("P")
            else:
                assert cube.faces[ff][fi] == "Y", f"corner {pos} has no yellow sticker"
                pattern.append("F")
    rotations = ["".join(pattern[i:] + pattern[:i]) for i in range(4)]
    return min(rotations)


def test_ocll_full_coverage():
    classes: dict[str, str] = {}
    for name in _OCLL_ALGS:
        cube = state_before(ALGORITHMS[name])
        cls = _ocll_class(cube)
        assert cls != "UUUU", f"{name} pre-state has all corners oriented"
        assert cls not in classes, f"{name} duplicates the case of {classes.get(cls)}"
        classes[cls] = name
    # There are exactly 7 non-solved OCLL classes; 7 distinct = full coverage.
    assert len(classes) == 7


# ── PLL arrows match the real piece permutation ──────────────────────


def _arrows_to_permutation(case) -> dict[str, str]:
    """The movement the diagram's arrows claim: position → destination."""
    perm = {}
    for a, b in list(case.swaps) + list(case.dashed_swaps):
        perm[a] = b
        perm[b] = a
    for cycle in case.cycles:
        for i, pos in enumerate(cycle):
            perm[pos] = cycle[(i + 1) % len(cycle)]
    return perm


def test_pll_arrows_match_permutation():
    for case in _pll_corner_cases() + _pll_edge_cases():
        cube = state_before(ALGORITHMS[case.label.removesuffix(" Perm")])
        real = _u_layer_permutation(cube)
        claimed = _arrows_to_permutation(case)
        for pos, dest in real.items():
            if pos == dest:
                assert pos not in claimed, f"{case.name}: arrow on solved piece {pos}"
            else:
                assert claimed.get(pos) == dest, (
                    f"{case.name}: piece at {pos} moves to {dest}, arrows say {claimed.get(pos)}"
                )


def test_pll_side_colors_match_prestate():
    """Every PLL diagram side sticker equals the algorithm's true pre-state color."""
    from cubepath.diagrams import _SIM_COLOR

    for case in _pll_corner_cases() + _pll_edge_cases():
        alg = ALGORITHMS[case.label.removesuffix(" Perm")]
        _, sides = _u_layer_views(state_before(alg))
        for side_name, attr in [
            ("top", case.top_side),
            ("right", case.right_side),
            ("bottom", case.bottom_side),
            ("left", case.left_side),
        ]:
            expected = [_SIM_COLOR[s] for s in sides[side_name]]
            assert attr == expected, f"{case.name} {side_name}: {attr} != {expected}"


# ── Step-diagram corner chirality ────────────────────────────────────
# A corner's three stickers wind around it with a fixed handedness — a
# diagram showing the mirror order depicts a physically impossible cube.
# The legal (U, F, R) triples are DERIVED from the simulator here, never
# hardcoded (hardcoding the set is exactly how the mirror bug shipped).

_HEX_TO_SIM = {v: k for k, v in _SIM_COLOR.items()}
# A dim sticker still names its face — that is the whole point of the tier —
# so the geometry checks below read through it rather than skipping it.
_HEX_TO_SIM |= {dim(v): k for k, v in _SIM_COLOR.items()}


def _ufr_triple(cube: Cube) -> tuple[str, str, str]:
    """The visible (U, F, R) stickers of the corner at up-front-right."""
    u, f, r = (cube.visible_sticker(face, 2, 2) for face in ("U", "F", "R"))
    return (u, f, r)


def _legal_ufr_triples() -> set[tuple[str, str, str]]:
    """All 24 legal (corner, twist) placements at UFR, read off whole-cube
    rotations of a solved cube — chirality-correct by construction."""
    triples = set()
    for r1 in ("", "x", "x2", "x'", "z", "z'"):
        for r2 in ("", "y", "y2", "y'"):
            c = Cube.solved()
            for r in (r1, r2):
                if r:
                    c.apply(r)
            triples.add(_ufr_triple(c))
    assert len(triples) == 24  # 8 corners × 3 twists, all distinct
    return triples


def _white_corner_triples_from_moves() -> set[tuple[str, str, str]]:
    """Every orientation the white-red-green corner reaches at UFR under face
    moves (breadth-first to depth 3) — the mechanical ground truth."""
    moves = [base + suffix for base in "RUFLBD" for suffix in ("", "'", "2")]
    found = set()
    frontier = [Cube.solved()]
    for _ in range(3):
        successors = []
        for cube in frontier:
            for m in moves:
                c2 = cube.copy()
                c2.apply_move(m)
                t = _ufr_triple(c2)
                if set(t) == {"W", "R", "G"}:
                    found.add(t)
                successors.append(c2)
        frontier = successors
    return found


def _all_step_diagrams():
    return (
        _step_cases()
        + _corner_case_steps()
        + _edge_case_steps()
        + [_orient_corner_case()]
        + _orient_corner_cases_15()
        + [_corner_pos_case()]
        + _align_edge_cases()
    )


def _step_ufr_triple(step) -> tuple[str, str, str] | None:
    """The diagram's (U, F, R) sticker triple at up-front-right, as simulator
    color letters — or None when any of the three has not been reached.

    Read off `_step_sticker_color` with the diagram's own `subject`, so this is
    the tiered colour the renderer emits, not a pre-tier one.
    """
    colors = tuple(
        _step_sticker_color(face, 2, 2, step.solved, step.face_colors, step.overrides, step.subject)
        for face in ("U", "F", "R")
    )
    if UNREACHED in colors:
        return None
    u, f, r = (_HEX_TO_SIM[c] for c in colors)
    return (u, f, r)


def test_white_corner_has_exactly_three_orientations():
    """Mechanical derivation sanity: face moves reach the white-red-green
    corner at UFR in exactly the 3 legal twists, matching the rotation set."""
    derived = _white_corner_triples_from_moves()
    from_rotations = {t for t in _legal_ufr_triples() if set(t) == {"W", "R", "G"}}
    assert len(derived) == 3
    assert derived == from_rotations


def test_step_diagram_corners_are_physically_possible():
    """Every fully-colored UFR corner in a step diagram is a legal orientation
    of a real corner — mirror-image sticker orders cannot ship."""
    legal = _legal_ufr_triples()
    checked = 0
    for step in _all_step_diagrams():
        triple = _step_ufr_triple(step)
        if triple is None:
            continue
        assert triple in legal, f"{step.filename}: impossible corner {triple} at (U, F, R)"
        checked += 1
    # solved, 3 corner insertions, orient_corner, orient_right, orient_front
    assert checked >= 7


def test_corner_insertion_cases_match_captions():
    """White Right/Front/Up show white on the R/F/U face, with the other two
    stickers in the (simulator-derived) legal order for that twist."""
    white_at = {"corner_right": 2, "corner_front": 1, "corner_up": 0}
    wrg = _white_corner_triples_from_moves()
    by_filename = {s.filename: s for s in _corner_case_steps()}
    assert by_filename.keys() == white_at.keys()
    for filename, w_index in white_at.items():
        (expected,) = (t for t in wrg if t[w_index] == "W")
        assert _step_ufr_triple(by_filename[filename]) == expected, filename


# ── Guide ↔ data consistency ─────────────────────────────────────────


def _algs_from_cell(cell: str) -> str:
    """Extract the algorithm from a markdown cell.

    Unwraps `[...]{.trig-*}` highlight spans (used with and without backticks)
    and strips backticks, leaving plain move text.
    """
    cell = re.sub(r"\[([^\]]+)\]\{[^}]*\}", r"\1", cell)
    return cell.replace("`", " ").strip()


def test_guide_tables_match_canonical_algorithms():
    """Every named algorithm in the guide's tables matches algs.py exactly."""
    text = GUIDE.read_text()
    checked = set()
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        name_match = None
        alg_cell = None
        for cell in cells:
            m = re.match(r"\*\*(.+?)\*\*", cell)
            if m:
                name_match = m.group(1).split("—")[0].strip()
            elif re.search(r"`[^`]+`", cell) and "figures/" not in cell:
                alg_cell = cell
        # Reference-table rows: | phase | alg | Name | step |
        if name_match is None and len(cells) == 4 and cells[0] in {"1", "1.5", "2", "3"}:
            name_match = cells[2]
            alg_cell = cells[1]
        if not name_match or not alg_cell or name_match not in ALGORITHMS:
            continue
        extracted = _algs_from_cell(alg_cell)
        if not extracted or "×" in extracted or "Repeat" in alg_cell:
            continue
        expected = parse_algorithm(ALGORITHMS[name_match])
        actual = parse_algorithm(extracted)
        assert actual == expected, f"{name_match}: guide has {actual}, algs.py has {expected}"
        checked.add(name_match)
    # Each core algorithm must be checked at least once (present in the guide).
    for required in ALGORITHMS:
        assert required in checked, f"{required} not found (or not checkable) in the guide"


def test_progression_table_totals_match_the_algorithm_set() -> None:
    """The guide's progression table is a running count of `algs.py`. It read
    "+0" for Phase 1.5 while that phase introduces the wide-f Hook, and its
    total stopped at ~18 for a 22-algorithm set. Derive it, don't retype it."""
    import re
    from pathlib import Path

    from cubepath.algs import ALGORITHMS

    guide = (Path(__file__).resolve().parents[3] / "guide" / "cubepath.md").read_text()
    rows = re.findall(r"^\| (\d[\d.]*): [^|]+\|\s*\+?(\d+)\s*\|\s*(\d+)\s*\|", guide, re.M)
    assert len(rows) == 4, f"progression table changed shape: {rows}"
    running = 0
    for phase, new, total in rows:
        running += int(new)
        assert running == int(total), f"phase {phase}: running total {running} != {total}"
    assert running == len(ALGORITHMS), (
        f"the table ends at {running} but algs.py holds {len(ALGORITHMS)}"
    )


def test_the_reference_table_phases_match_the_progression_deltas() -> None:
    """The guide states each algorithm's phase twice — as a column in the
    Algorithm Reference table and as a delta in the Progression table — and
    nothing made them agree. They did not: the reference table put both Orient
    Corners finishers in Phase 1.5 while the progression's "Phase 1 = 9" could
    only be reached by counting them in Phase 1, which has 7 named algorithms.
    Count first appearances per phase and hold the two tables to each other."""
    from cubepath.algs import ALGORITHMS

    text = GUIDE.read_text()
    seen: set[str] = set()
    new_per_phase: dict[str, int] = {}
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] not in {"1", "1.5", "2", "3"}:
            continue
        name = cells[2]
        # The em-dash row is Phase 1's "repeat the sexy move and flip" — a
        # technique with no name, deliberately not one of the counted set.
        if name not in ALGORITHMS or name in seen:
            continue
        seen.add(name)
        new_per_phase[cells[0]] = new_per_phase.get(cells[0], 0) + 1

    assert seen == set(ALGORITHMS), (
        f"reference table and algs.py disagree: {seen ^ set(ALGORITHMS)}"
    )
    rows = re.findall(r"^\| (\d[\d.]*): [^|]+\|\s*\+?(\d+)\s*\|", text, re.M)
    deltas = {phase: int(new) for phase, new in rows}
    assert deltas == new_per_phase, (
        f"progression deltas {deltas} != first appearances in the reference table {new_per_phase}"
    )


def test_the_lessons_and_the_guide_agree_on_how_many_algorithms_are_in_use() -> None:
    """The guide counts algorithms LEARNED (22); the lessons quote the number in
    DAILY USE. Both numbers are true and they are not the same, which is exactly
    how they drifted — the progression table was corrected to 22 and the lesson
    prose went on saying "about 18" for a set that has never been 18. Derive the
    in-use count from `algs.py` and pin every place that states it, so the next
    edit to either surface has to touch the source of truth."""
    from pathlib import Path

    from cubepath.algs import ALGORITHMS, RETIRED_AT_CFOP_SWITCH, in_daily_use

    assert RETIRED_AT_CFOP_SWITCH <= set(ALGORITHMS), (
        f"retired names not in ALGORITHMS: {RETIRED_AT_CFOP_SWITCH - set(ALGORITHMS)}"
    )
    in_use = len(in_daily_use())
    assert in_use == len(ALGORITHMS) - len(RETIRED_AT_CFOP_SWITCH)

    # Independent cross-check: the same total by step, so a name added to
    # ALGORITHMS without a step assignment cannot slip through.
    last_layer = {
        "F-sexy-F'",
        "f-sexy-f'",  # OE
        "Sune",
        "Anti-Sune",
        "Pi",
        "Headlights",
        "Double Headlights",
        "Chameleon",
        "Bowtie",  # OC
        "T-Perm",
        "Y-Perm",  # PC
        "Ua",
        "Ub",
        "H-Perm",
        "Z-Perm",  # PE
    }
    below = {"Sexy Move", "Lefty", "Edge Insert Right", "Edge Insert Left"}
    assert last_layer | below == set(in_daily_use()), (
        "the step breakdown and the retired set disagree about what is in use"
    )
    assert len(last_layer) == 15 and len(below) == 4 and in_use == 19

    lessons = Path(__file__).resolve().parents[3] / "app" / "src" / "content" / "lessons"
    words = {19: ("19", "nineteen")}[in_use]

    for name in ("course-complete.mdx", "cfop-switch.mdx"):
        text = (lessons / name).read_text()
        assert any(w in text for w in words), f"{name} never states the in-use count {in_use}"
        # The stale claim, in either spelling, must be gone from both.
        assert "about 18" not in text and "eighteen" not in text, (
            f"{name} still carries the pre-derivation algorithm count"
        )

    guide = GUIDE.read_text()
    assert f"**{in_use}**" in guide, "the guide's progression note lost the in-use count"
    for retired in RETIRED_AT_CFOP_SWITCH:
        stem = retired.replace("Orient Corners ", "Orient Corners")
        assert retired in guide or stem.split()[0] in guide, (
            f"the guide never names the retired algorithm {retired}"
        )


# ── F2L (41 slot-and-pair cases) ─────────────────────────────────────
# The F2L set is the largest single group in the app and the only one drawn as
# a 3D isometric case rather than a plan view, so these tests hold the whole
# design to the data: the slot is where the simulator says it is, the pair is
# the pair the slot wants, the three tiers mean what they claim, and — the one
# that matters most — the picture is a state the algorithm printed beside it
# actually solves.

_F2L_RAW = _APP_DATA / "f2l-raw.json"


def _f2l_raw() -> list[dict[str, Any]]:
    return list(json.loads(_F2L_RAW.read_text())["f2l"])


def test_f2l_slot_is_derived_from_the_move_tables() -> None:
    """The FR slot is found by intersecting layers, never written down. R∩F∩D
    is the DFR corner; R∩F minus the U and D layers is the FR edge."""
    corner, edge = _fr_slot()
    assert sorted(corner) == [("D", 2), ("F", 8), ("R", 6)]
    assert sorted(edge) == [("F", 5), ("R", 3)]
    solved = Cube.solved()
    assert {solved.faces[f][i] for f, i in corner} == {"W", "R", "G"}
    assert {solved.faces[f][i] for f, i in edge} == {"R", "G"}


def test_f2l_case_count_and_names() -> None:
    cases = f2l_cases()
    assert len(cases) == 41
    assert [c.name for c in cases] == [f"f2l_{n:02d}" for n in range(1, 42)]
    assert len({c.name for c in cases}) == 41
    assert all(c.subdir == "f2l" for c in cases)


def test_f2l_marks_the_slot_on_the_near_vertical_edge() -> None:
    """The two visible faces of the FR slot, which is where the projection puts
    the eye. Same set for every case: the slot does not move, the pair does."""
    for case in f2l_cases():
        assert case.slot == frozenset({("F", 2, 0), ("F", 2, 1), ("R", 2, 0), ("R", 2, 1)}), (
            case.name
        )


def test_f2l_colours_cover_every_visible_facelet() -> None:
    every = {(f, a, b) for f in ("U", "F", "R") for a in range(3) for b in range(3)}
    for case in f2l_cases():
        assert set(case.colors) == every, case.name


def test_f2l_tiers_are_what_they_claim() -> None:
    """Highlight is exactly the pair, dim is exactly the already-solved first
    two layers, grey is exactly the last layer plus the unfilled slot — checked
    against an independent re-derivation from the setup, not against the
    generator's own bookkeeping."""
    corner, edge = _fr_slot()
    slot_home = corner | edge
    u_layer = _layer("U")
    dim_tones = {dim(c) for c in _SIM_COLOR.values()}
    full_tones = set(_SIM_COLOR.values())

    seen_pair_counts: Counter[int] = Counter()
    for raw, case in zip(_f2l_raw(), f2l_cases(), strict=True):
        cube = Cube.solved()
        cube.apply(raw["setup"])
        traced = _traced()
        traced.apply(raw["setup"])
        pair = {
            p
            for p in _ALL_FACELETS
            if traced.faces[p[0]][p[1]] in {f"{f}{i}" for f, i in slot_home}
        }
        assert len(pair) == 5, f"{case.name}: a corner and an edge is five facelets"

        highlight = dim_count = grey_count = 0
        for (f, a, b), colour in case.colors.items():
            sim_face, row, col = diagram_to_sim(f, a, b)
            p = (sim_face, row * 3 + col)
            if p in pair:
                assert colour in full_tones, f"{case.name}: pair facelet {f}{a}{b} not full colour"
                assert colour == _SIM_COLOR[cube.faces[sim_face][row * 3 + col]]
                highlight += 1
            elif p in slot_home or p in u_layer:
                assert colour == UNREACHED, f"{case.name}: {f}{a}{b} should be not-reached"
                grey_count += 1
            else:
                assert colour in dim_tones, f"{case.name}: {f}{a}{b} should be dim"
                assert cube.faces[sim_face][row * 3 + col] == COLORS[sim_face], (
                    f"{case.name}: {f}{a}{b} is dimmed as solved but is not"
                )
                dim_count += 1
        # 8 dim: the F and R centres, and on each of those faces the bottom-row
        # corner sticker, the bottom-row edge sticker and the middle-row edge
        # sticker of a finished slot. Plus the U centre, which a U turn does not
        # move — so the hold stays legible instead of going blank.
        assert dim_count == 9, f"{case.name}: dim region changed size"
        assert highlight + dim_count + grey_count == 27
        seen_pair_counts[highlight] += 1

    # Measured, not hoped for: 18 cases show the whole pair, and the other 23
    # hide exactly one facelet — which the two visible ones of that piece
    # determine, since the FR edge is *the* red/green edge.
    assert dict(seen_pair_counts) == {5: 18, 4: 23}


def test_f2l_diagram_is_a_state_its_own_algorithm_solves() -> None:
    """The gate that makes the picture trustworthy: run the case's printed
    algorithm on the state the diagram draws, and the first two layers must be
    finished — up to a whole-cube rotation, because a dozen of the algs start
    with `y`.

    One case is skipped, and the skip is pinned rather than swallowed: F2L 32's
    primary alg is `(U R U' R')3`, a postfix group repeat that `cube.py`
    deliberately refuses (it accepts the `×N` spelling only). That is a real
    notation gap between the repo's verified data and its own simulator, not a
    property of this diagram — `verify-f2l.mjs` checks the alg on the kpuzzle.
    When the parser learns that spelling this list must shrink to empty.
    """
    first_two = [p for p in _ALL_FACELETS if p not in _layer("U")]
    skipped = []
    for raw in _f2l_raw():
        cube = Cube.solved()
        cube.apply(raw["setup"])
        try:
            cube.apply(raw["algs"][0])
        except UnsupportedNotationError:
            skipped.append(raw["number"])
            continue
        solved_somewhere = False
        for rot in _ROTATIONS:
            probe = cube.copy()
            if rot:
                probe.apply(rot)
            if all(probe.faces[f][i] == COLORS[f] for f, i in first_two):
                solved_somewhere = True
                break
        assert solved_somewhere, f"F2L {raw['number']}: its own algorithm does not solve it"
    assert skipped == [32], f"the notation gap moved: {skipped}"


# ── Beginner case icons draw the state their algorithm solves ─────────
# The four paired lesson figures are also the /reference icons of the four
# beginner cases the app pins to these same algs.py strings. Each pair differs
# only in where the yellow (or matching) sticker sits, so an icon swapped for
# its twin is a wrong picture that no existence check can see. The overrides
# are what the picture paints; they must be the stickers of `state_before`.


@functools.lru_cache(maxsize=1)
def _step_by_filename():
    """Every `StepDiagram` by the file it renders to. Built once, not per case."""
    from cubepath.diagrams import all_steps

    return {s.filename: s for s in all_steps()}


@pytest.mark.parametrize(
    ("filename", "algorithm", "unrotate"),
    [
        ("orient_right", "Orient Corners Right", ""),
        ("orient_front", "Orient Corners Front", ""),
        # An insert ends turned by `y` / `y'`; the reader's frame is the one
        # BEFORE the turn, so the solved cube is turned first and the inverse
        # applied after, exactly as the app's tests read the same strings.
        ("edge_right", "Edge Insert Right", "y"),
        ("edge_left", "Edge Insert Left", "y'"),
    ],
)
def test_beginner_case_icons_draw_the_state_their_algorithm_solves(
    filename: str, algorithm: str, unrotate: str
) -> None:
    from cubepath.cube import invert_algorithm

    # A bare `next()` here raises StopIteration, which pytest reports as an
    # ERROR with no message rather than "this figure was renamed" — and the
    # whole step list is rebuilt once per parameter set for one lookup.
    step = _step_by_filename().get(filename)
    assert step is not None, f"no step diagram named {filename}"
    assert step.overrides, f"{filename} paints nothing"
    cube = Cube.solved()
    if unrotate:
        cube.apply(unrotate)
    cube.apply(invert_algorithm(ALGORITHMS[algorithm]))
    for face in "UDFBLR":
        assert cube.sticker_at(face, 1, 1) == COLORS[face], f"{filename}: centres not home"
    for (face, a, b), colour in step.overrides.items():
        sim_face, row, col = diagram_to_sim(face, a, b)
        actual = _SIM_COLOR[cube.sticker_at(sim_face, row, col)]
        assert colour == actual, f"{filename} paints {face}{a}{b} {colour}, the case has {actual}"
