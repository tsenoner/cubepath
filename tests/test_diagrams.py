"""Tests for cubepath diagram generation."""

from cubepath.cube import Cube
from cubepath.diagrams import (
    _CENTERS,
    _CORNERS_POSITIONED,
    _EDGES_ALIGNED,
    _FIRST_LAYER,
    _SECOND_LAYER,
    _YELLOW_CROSS,
    BLUE,
    GREEN,
    GREY,
    ORANGE,
    RED,
    YELLOW,
    _align_edge_cases,
    _arrow_pos,
    _corner_case_steps,
    _corner_pos_case,
    _edge_case_steps,
    _n_sticker_color,
    _notation_moves,
    _orient_corner_case,
    _orient_corner_cases_15,
    _pll_corner_cases,
    _pll_edge_cases,
    _step_cases,
    all_cases,
    render,
    render_notation,
    render_overview,
    render_step,
)

# ViewBox dimensions (computed from layout constants)
VIEWBOX_SIZE = 192


def test_all_cases_count():
    assert len(all_cases()) == 16


def test_case_names_unique():
    cases = all_cases()
    names = [c.name for c in cases]
    assert len(names) == len(set(names))


def test_render_creates_svg(tmp_path):
    case = all_cases()[0]
    path = render(case, tmp_path)
    assert path.exists()
    assert path.suffix == ".svg"
    content = path.read_text()
    assert "<svg" in content


def test_arrows_within_viewbox():
    valid_names = {"top", "bottom", "left", "right", "tl", "tr", "bl", "br"}
    for name in valid_names:
        x, y = _arrow_pos(name)
        assert 0 <= x <= VIEWBOX_SIZE, f"{name}: x={x} out of bounds"
        assert 0 <= y <= VIEWBOX_SIZE, f"{name}: y={y} out of bounds"


def test_svg_contains_expected_rects(tmp_path):
    """9 U-face + 12 side stickers + 1 background = 22 rects."""
    case = all_cases()[0]
    path = render(case, tmp_path)
    content = path.read_text()
    assert content.count("<rect") == 22


def test_oll_cases_have_no_arrows():
    for case in all_cases():
        if case.category.startswith("oll"):
            assert not case.swaps, f"{case.name} has swaps"
            assert not case.cycles, f"{case.name} has cycles"


def test_pll_cases_have_arrows():
    for case in all_cases():
        if case.category.startswith("pll"):
            assert case.swaps or case.cycles, f"{case.name} has no arrows"


def test_step_cases_count():
    assert len(_step_cases()) == 8


def test_step_render_creates_svg(tmp_path):
    steps = _step_cases()
    for step in steps:
        path = render_step(step, tmp_path)
        assert path.exists()
        assert path.suffix == ".svg"
        content = path.read_text()
        assert "<svg" in content


def test_orient_corner_cases_15():
    cases = _orient_corner_cases_15()
    assert len(cases) == 2
    assert cases[0].filename == "orient_right"
    assert cases[1].filename == "orient_front"


def test_solve_state_progression():
    assert _CENTERS < _FIRST_LAYER < _SECOND_LAYER < _YELLOW_CROSS
    assert _YELLOW_CROSS < _EDGES_ALIGNED < _CORNERS_POSITIONED


# ── Sticker color rules vs simulator ────────────────────────────────

# Map diagram sticker colors to simulator single-char color codes
_COLOR_TO_SIM = {
    YELLOW: "Y",
    RED: "R",
    GREEN: "G",
    ORANGE: "O",
    BLUE: "B",
    "#FFFFFF": "W",
}


def test_sticker_color_rules_match_simulator():
    """For each notation move, verify diagram sticker colors match simulator state.

    This is the highest-value test: it catches any mismatch between the
    hand-coded _STICKER_COLOR_RULES table and actual cube physics.
    """
    # Map notation move layer+CW to algorithm string for the simulator
    _MOVE_ALG = {
        ("R", True): "R",
        ("R", False): "R'",
        ("R2", True): "R2",
        ("U", True): "U",
        ("L", True): "L",
        ("F", True): "F",
        ("D", True): "D",
        ("B", True): "B",
        ("M", True): "M",
        ("S", True): "S",
        ("E", True): "E",
        ("r", True): "r",
        ("x", True): "x",
        ("y", True): "y",
        ("z", True): "z",
    }
    mismatches = []
    for move in _notation_moves():
        key = (move.layer, move.clockwise)
        alg = _MOVE_ALG.get(key)
        if alg is None:
            continue
        cube = Cube.solved()
        cube.apply(alg)
        for face in ("U", "F", "R"):
            for a in range(3):
                for b in range(3):
                    rule_color = _n_sticker_color(face, a, b, move.layer, move.clockwise)
                    sim_color_char = cube.visible_sticker(face, a, b)
                    rule_char = _COLOR_TO_SIM.get(rule_color)
                    if rule_char is None:
                        continue
                    if rule_char != sim_color_char:
                        mismatches.append(
                            f"{move.name}: {face}({a},{b}) rule={rule_char} sim={sim_color_char}"
                        )
    assert mismatches == [], "Sticker color mismatches:\n" + "\n".join(mismatches)


# ── PLL side-color verification ─────────────────────────────────────

# Map diagram colors to sim color chars
_DIAG_TO_SIM = {RED: "R", GREEN: "G", BLUE: "B", ORANGE: "O", YELLOW: "Y", GREY: "?"}

# Map plan-view side positions to simulator face + col for the edge sticker
# top_side[0..2] = B face top row (left-to-right in plan view)
# right_side[0..2] = R face top row
# bottom_side[0..2] = F face top row
# left_side[0..2] = L face top row
_PLL_ALGORITHMS = {
    "pll_tperm": "R U R' U' R' F R2 U' R' U' R U R' F'",
    "pll_yperm": "F R U' R' U' R U R' F' R U R' U' R' F R F'",
    "pll_ua": "R U' R U R U R U' R' U' R2",
    "pll_ub": "R2 U R U R' U' R' U' R' U R'",
    "pll_hperm": "M2 U' M2 U2 M2 U' M2",
}


def test_pll_edge_cases_have_correct_corner_colors():
    """PLL edge cases (Ua, Ub, H, Z) should show correct corner colors (all same per face)."""
    for case in _pll_edge_cases():
        # Edge PLLs don't move corners, so each side should have matching corner stickers
        for side_name, side in [
            ("top", case.top_side),
            ("right", case.right_side),
            ("bottom", case.bottom_side),
            ("left", case.left_side),
        ]:
            assert side[0] == side[2], (
                f"{case.name} {side_name}: corners don't match ({side[0]} vs {side[2]})"
            )


def test_pll_corner_cases_have_grey_edges():
    """PLL corner cases use GREY for edge stickers (not relevant to corner swaps)."""
    for case in _pll_corner_cases():
        for side_name, side in [
            ("top", case.top_side),
            ("right", case.right_side),
            ("bottom", case.bottom_side),
            ("left", case.left_side),
        ]:
            assert side[1] == GREY, f"{case.name} {side_name}: edge should be GREY, got {side[1]}"


# ── Render smoke tests ──────────────────────────────────────────────


def test_render_notation_all(tmp_path):
    """All 15 notation move SVGs render and contain <svg>."""
    moves = _notation_moves()
    assert len(moves) == 15
    for move in moves:
        path = render_notation(move, tmp_path)
        assert path.exists(), f"{move.filename} not created"
        content = path.read_text()
        assert "<svg" in content, f"{move.filename} missing <svg>"


def test_render_overview(tmp_path):
    path = render_overview(tmp_path)
    assert path.exists()
    content = path.read_text()
    assert "<svg" in content


def test_sub_case_counts():
    assert len(_corner_case_steps()) == 3
    assert len(_edge_case_steps()) == 2
    assert len(_align_edge_cases()) == 2


def test_all_step_diagrams_render(tmp_path):
    """All 19 step diagrams render without error."""
    all_steps = [
        *_step_cases(),
        *_corner_case_steps(),
        *_edge_case_steps(),
        _orient_corner_case(),
        *_orient_corner_cases_15(),
        _corner_pos_case(),
        *_align_edge_cases(),
    ]
    assert len(all_steps) == 19
    for step in all_steps:
        path = render_step(step, tmp_path)
        assert path.exists(), f"{step.filename} not created"
        content = path.read_text()
        assert "<svg" in content, f"{step.filename} missing <svg>"
