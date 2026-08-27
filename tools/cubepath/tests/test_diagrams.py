"""Tests for cubepath diagram generation."""

import filecmp
import itertools
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from cubepath.cube import Cube
from cubepath.diagrams import (
    _CENTERS,
    _CORNERS_POSITIONED,
    _EDGES_ALIGNED,
    _FIRST_LAYER,
    _SECOND_LAYER,
    _THEME_CSS,
    _YELLOW_CROSS,
    ARROW_COLOR,
    BLUE,
    CARD,
    CARD_FACES,
    DARK_INK,
    GREEN,
    GREY,
    ORANGE,
    RED,
    SCREEN,
    SCREEN_FACES,
    WHITE,
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
    all_steps,
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
    assert 'y="20"' in screen and 'y="12"' in card
    assert 'y="160"' in screen and 'y="160"' in card


# ── Theming ───────────────────────────────────────────────────────────
# The 130 generated SVGs are loaded as plain <img src>, which cannot see the
# page's CSS custom properties, so each one carries its own colour-scheme
# rules. resvg (typst) skips every @media block, which is what leaves the
# guide PDF with the opaque plate it needs behind the 13 figures that sit in a
# tinted `.algorithm` callout. These tests pin all three halves of that: the
# block is emitted, the print style is exempt, and the two shipped trees agree.

_REPO = Path(__file__).resolve().parents[3]
_GUIDE_SVG = _REPO / "guide" / "figures" / "generated"
_APP_SVG = _REPO / "app" / "public" / "diagrams"
_SVG_DIRS = ("oll", "oll-full", "pll", "pll-full", "steps", "notation")


def _themed_renders(tmp_path) -> dict[str, str]:
    """One output from each of the four screen render entry points."""
    return {
        "render": render(all_cases()[0], tmp_path / "r").read_text(),
        "render_step": render_step(_step_cases()[0], tmp_path / "s").read_text(),
        "render_notation": render_notation(_notation_moves()[0], tmp_path / "n").read_text(),
        "render_overview": render_overview(tmp_path / "o").read_text(),
    }


def test_screen_diagrams_carry_a_theme_block(tmp_path) -> None:
    for name, content in _themed_renders(tmp_path).items():
        assert "prefers-color-scheme" in content, f"{name}: no colour-scheme rules"
        assert content.count('class="bg"') == 1, f"{name}: expected exactly one plate"


def test_no_screen_diagram_paints_an_unconditional_plate(tmp_path) -> None:
    """The bug this fixes: an opaque plate that no theme can turn off. The
    `fill=` attribute stays as the no-CSS fallback, but a class rule beats it
    everywhere, so the plate must be reachable by one."""
    for name, content in _themed_renders(tmp_path).items():
        plates = re.findall(r"<rect[^>]*/>", content)
        opaque = [r for r in plates if f'fill="{WHITE}"' in r and "rx=" in r]
        assert opaque, f"{name}: no plate found at all"
        for rect in opaque:
            assert 'class="bg"' in rect, f"{name}: unreachable opaque plate {rect}"


def test_the_web_plate_is_transparent_in_both_schemes() -> None:
    """The user-visible fix: on a page the diagram sits on the page surface,
    not on a second card. Both browser branches drop it; the media-free
    default is what resvg keeps for print, and it must stay opaque."""
    assert _THEME_CSS.startswith(f".bg{{fill:{WHITE}}}"), "print default lost its plate"
    for scheme in ("light", "dark"):
        head, _, tail = _THEME_CSS.partition(f"@media (prefers-color-scheme:{scheme}){{")
        assert tail, f"no {scheme} block"
        assert tail.split("}}")[0].count("fill:none") == 1, f"{scheme} still paints a plate"


def test_theme_css_uses_the_module_constants() -> None:
    """The T2 lesson: colour must never be respelled beside the palette."""
    assert WHITE in _THEME_CSS
    assert ARROW_COLOR in _THEME_CSS
    assert DARK_INK in _THEME_CSS


def test_labels_and_axis_dots_are_ink_tagged(tmp_path) -> None:
    """These sit on the plate, not on a sticker, so they vanish on a dark page
    unless they flip with it."""
    notation = render_notation(_notation_moves()[0], tmp_path / "n").read_text()
    assert re.search(r'<text[^>]*class="ink"', notation), "move label not tagged"

    overview = render_overview(tmp_path / "o").read_text()
    assert len(re.findall(r'<text[^>]*class="ink"', overview)) == 6
    assert len(re.findall(r'<circle[^>]*class="ink"', overview)) == 6
    assert 'fill="#222"' not in overview and 'fill="#222"' not in notation


def test_card_diagrams_are_not_themed(tmp_path) -> None:
    """A printed card is ink on paper: no page behind it to show through."""
    assert CARD.themed is False and SCREEN.themed is True
    for content in (
        render(all_cases()[0], tmp_path / "r", style=CARD).read_text(),
        render_step(_step_cases()[0], tmp_path / "s", style=CARD).read_text(),
    ):
        assert "@media" not in content
        assert "<style" not in content, "a card carries no stylesheet at all"
        # The plate keeps its class — an inert hook with no rules to match it —
        # so `_bg` stays one code path, and its `fill=` is what actually prints.
        assert f'<rect class="bg" fill="{WHITE}"' in content


def test_ribbon_occluders_stay_opaque_white(tmp_path) -> None:
    """The overview's ~30 arrow occluders carry their own surface. Theming
    them punches dark holes straight through the cube."""
    overview = render_overview(tmp_path / "o").read_text()
    occluders = re.findall(f'fill="{WHITE}"', overview)
    assert len(occluders) >= 30, "occluders lost their literal white"
    assert 'class="occ"' not in overview


def test_committed_diagrams_match_the_generator(tmp_path) -> None:
    """`make diagrams` is the only way these files change — a hand-edit fails
    here, the same contract test_logo.py holds over the favicon. Covers the
    diagrams this module owns; `fullsets.py`'s 78 are covered by the two
    whole-tree tests below."""
    fresh = tmp_path / "gen"
    for case in all_cases():
        render(case, fresh)
    for step in all_steps():
        render_step(step, fresh)
    for move in _notation_moves():
        render_notation(move, fresh)
    render_overview(fresh)

    stale = [
        str(p.relative_to(fresh))
        for p in sorted(fresh.rglob("*.svg"))
        if (_GUIDE_SVG / p.relative_to(fresh)).read_text() != p.read_text()
    ]
    assert not stale, f"committed SVGs differ from the generator: {stale}"


def test_the_two_diagram_trees_are_byte_identical() -> None:
    """app/public/diagrams is a literal copy of guide/figures/generated made by
    scripts/sync-diagrams.sh. Nothing else gated that, so the app could ship a
    stale diagram indefinitely."""
    for sub in _SVG_DIRS:
        guide_dir, app_dir = _GUIDE_SVG / sub, _APP_SVG / sub
        assert app_dir.is_dir(), f"{sub}/ never synced into the app"
        names = sorted(p.name for p in guide_dir.glob("*.svg"))
        assert names == sorted(p.name for p in app_dir.glob("*.svg")), f"{sub}/ file sets differ"
        match, mismatch, errors = filecmp.cmpfiles(guide_dir, app_dir, names, shallow=False)
        assert not mismatch and not errors, f"{sub}/ drifted: {mismatch + errors}"


def test_every_shipped_diagram_is_themed() -> None:
    """The regression the user actually reported, asserted over the real
    shipped tree rather than a fresh render."""
    svgs = sorted(_APP_SVG.rglob("*.svg"))
    assert len(svgs) == 130, f"expected 130 diagrams, found {len(svgs)}"
    for svg in svgs:
        content = svg.read_text()
        assert "prefers-color-scheme" in content, f"{svg.name} has no colour-scheme rules"
        assert 'class="bg"' in content, f"{svg.name} has an unreachable plate"


needs_typst = pytest.mark.skipif(
    not all(shutil.which(t) for t in ("typst", "pdftoppm")),
    reason="needs typst + poppler",
)


@needs_typst
def test_the_pdf_never_sees_the_media_block(tmp_path) -> None:
    """The load-bearing claim behind one file serving both outputs: resvg
    applies the class rules but skips every @media, so the plate the guide
    needs survives while the web drops it. Rendered, not assumed — 13 figures
    sit inside a tinted `.algorithm` callout and would otherwise show it."""
    tint = "#e8f4fd"  # callouts.lua, `.algorithm` bg
    svg = render(all_cases()[0], tmp_path)
    # typst resolves paths against --root, so keep the figure beside the source
    shutil.copy(svg, tmp_path / "figure.svg")
    src = tmp_path / "proof.typ"
    src.write_text(
        f'#set page(width: 192pt, height: 192pt, margin: 0pt, fill: rgb("{tint}"))\n'
        '#image("figure.svg", width: 192pt, height: 192pt)\n'
    )
    subprocess.run(
        ["typst", "compile", "--root", str(tmp_path), str(src), str(tmp_path / "p.pdf")],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["pdftoppm", "-r", "36", str(tmp_path / "p.pdf"), str(tmp_path / "out")],
        check=True,
        capture_output=True,
    )
    header, dims, _, pixels = (tmp_path / "out-1.ppm").read_bytes().split(b"\n", 3)
    assert header == b"P6"
    w, h = (int(v) for v in dims.split())

    def px(x: int, y: int) -> tuple[int, int, int]:
        i = (y * w + x) * 3
        return tuple(pixels[i : i + 3])

    # Inside the plate: opaque white. Outside its corner radius: the page tint,
    # which is also what the whole figure would look like if @media had applied.
    assert px(6, 6) == (255, 255, 255), "the guide PDF lost its background plate"
    assert px(4, h // 2) == (255, 255, 255)
    assert px(0, 0) == (232, 244, 253), "sampled the wrong pixel — tint not visible"
