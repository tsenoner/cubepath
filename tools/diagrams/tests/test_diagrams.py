"""Tests for cubepath diagram generation."""

import itertools

from cubepath.cube import Cube
from cubepath.diagrams import (
    _CENTERS,
    _CORNERS_POSITIONED,
    _EDGES_ALIGNED,
    _FIRST_LAYER,
    _SECOND_LAYER,
    _YELLOW_CROSS,
    BLUE,
    CARD,
    CARD_FACES,
    GREEN,
    GREY,
    ORANGE,
    RED,
    SCREEN,
    SCREEN_FACES,
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
from cubepath.palette import contrast

# ViewBox dimensions (computed from layout constants)
VIEWBOX_SIZE = 192


def test_all_cases_count():
    assert len(all_cases()) == 17


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


def test_pll_corner_cases_show_true_edge_colors():
    """PLL corner cases show real (non-grey) edge sticker colors from the pre-state."""
    for case in _pll_corner_cases():
        for side in (case.top_side, case.right_side, case.bottom_side, case.left_side):
            assert GREY not in side, f"{case.name}: grey sticker in side strip"


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


# ── Card style: greyscale legibility and band thickness ───────────────
# A card is printed, often on a mono laser, at under 5 mm per sticker. These
# gate the palette by measurement so nobody re-picks a colour by eye.

_SIDE_FACES = ("R", "G", "O", "B")  # red, green, orange, blue
CARD_SIDE_CONTRAST_MIN = 1.95


def test_card_side_faces_are_separable_in_greyscale() -> None:
    for a, b in itertools.combinations(_SIDE_FACES, 2):
        ratio = contrast(CARD_FACES[a], CARD_FACES[b])
        assert ratio >= CARD_SIDE_CONTRAST_MIN, f"{a}/{b} at {ratio:.2f}:1 prints as one grey"


def test_card_palette_beats_the_screen_palette_on_every_side_pair() -> None:
    """Not a tie-break: the card palette exists only because it separates
    better. If an edit makes any pair worse, it is the wrong edit."""
    for a, b in itertools.combinations(_SIDE_FACES, 2):
        card, screen = (
            contrast(CARD_FACES[a], CARD_FACES[b]),
            contrast(SCREEN_FACES[a], SCREEN_FACES[b]),
        )
        assert card > screen, f"{a}/{b} got worse: {screen:.2f} -> {card:.2f}"


def test_masked_grey_is_readable_against_yellow() -> None:
    """The whole job of an OLL diagram: solved sticker vs not. On screen this
    is 1.28:1 — ten identical grey squares on a mono printer."""
    assert contrast(SCREEN_FACES["Y"], SCREEN.masked) < 1.5
    assert contrast(CARD_FACES["Y"], CARD.masked) >= 4.0


def test_card_bands_grow_outward_only(tmp_path) -> None:
    """A thicker side band must not move the inner edge, or every diagram
    size measured for the card silently changes."""
    case = _pll_edge_cases()[0]
    screen = render(case, tmp_path / "s", style=SCREEN).read_text()
    card = render(case, tmp_path / "c", style=CARD).read_text()

    assert 'viewBox="0 0 192 192"' in screen
    assert 'viewBox="0 0 192 192"' in card, "card render changed the viewBox"

    assert f'height="{SCREEN.band_u}"' in screen
    assert f'height="{CARD.band_u}"' in card
    # inner edge pinned: top band ends at 32, bottom band starts at 160
    assert f'height="{SCREEN.band_u}"' in screen and 'y="20"' in screen
    assert f'height="{CARD.band_u}"' in card and 'y="12"' in card
    assert 'y="160"' in screen and 'y="160"' in card
