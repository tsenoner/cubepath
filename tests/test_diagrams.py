"""Tests for cubepath diagram generation."""

from cubepath.diagrams import (
    _arrow_pos,
    _orient_corner_cases_15,
    _step_cases,
    all_cases,
    render,
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
