"""Tests for the brand mark generator.

The point of these is drift: `app/public/favicon.svg` is the source every icon
is rasterized from, so a hand-edit there — or a change here that silently moves
the geometry — must fail the gate rather than ship a mark nobody generated.
"""

import re

from cubepath.logo import (
    FACES,
    LIGHT,
    TRAIL,
    TRAIL_COLOR,
    face_point,
    favicon_path,
    project,
    render,
    rounded_path,
    shapes,
    union_loops,
)


def test_committed_favicon_matches_generator() -> None:
    """The shipped favicon is exactly what this module produces."""
    assert favicon_path().read_text() == render(), (
        "app/public/favicon.svg is out of sync — run `uv run cubepath-logo`, "
        "then `node scripts/gen-icons.mjs` in app/"
    )


def test_output_is_deterministic() -> None:
    assert render() == render()


def test_path_count() -> None:
    """Silhouette + 27 stickers - 7 trail cells + 2 merged trail loops."""
    assert len(shapes()) == 1 + (27 - 7) + 2


def test_every_path_is_closed_and_finite() -> None:
    for _cls, d in shapes():
        assert d.startswith("M") and d.endswith("Z")
        for value in re.findall(r"-?\d+\.\d+", d):
            assert 0.0 <= float(value) <= 64.0, f"{value} escapes the viewBox"


def test_trail_cells_are_not_drawn_twice() -> None:
    """Trail stickers are skipped in the grid pass and drawn as merged loops."""
    classes = [cls for cls, _ in shapes()]
    assert classes.count("t") == 2  # one loop on U, one on F
    assert classes.count("f") == 9 - len(TRAIL["F"])
    assert classes.count("u") == 9 - len(TRAIL["U"])
    assert classes.count("r") == 9  # the route never reaches the right face


def test_faces_share_the_centre_vertex() -> None:
    """All three visible faces meet at the cube's near-top corner."""
    assert project(3, 3, 3) == project(*FACES["U"][2]) == project(*FACES["F"][1])


def test_projection_is_symmetric() -> None:
    """The silhouette is mirror-symmetric about the vertical axis."""
    left = face_point("F", 0, 3)  # cube's lower-left vertex
    right = face_point("R", 0, 3)  # lower-right vertex
    assert left[0] + right[0] == 32.0 * 2
    assert left[1] == right[1]


def test_union_loops_merges_adjacent_cells() -> None:
    """Two side-by-side cells trace one 6-corner outline, not two squares."""
    loops = union_loops({(0, 0), (1, 0)})
    assert len(loops) == 1
    assert len(loops[0]) == 6


def test_union_loops_separates_disjoint_cells() -> None:
    loops = union_loops({(0, 0), (2, 2)})
    assert len(loops) == 2


def test_rounded_path_clamps_radius_to_the_shortest_edge() -> None:
    """A radius larger than the shape cannot invert its corners."""
    square = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    for value in re.findall(r"-?\d+\.\d+", rounded_path(square, radius=99.0)):
        assert 0.0 <= float(value) <= 2.0


def test_theme_blocks_cover_the_same_face_classes() -> None:
    """Dark mode must restyle every face, or part of the mark vanishes on a dark card."""
    svg = render()
    dark_block = svg.split("prefers-color-scheme:dark)")[1]
    for cls in LIGHT:
        assert f".{cls}{{fill:" in dark_block, f"class {cls} has no dark-mode fill"


def test_trail_colour_is_the_brand_yellow_in_both_themes() -> None:
    """The route is the constant across themes; only the cube's faces move."""
    svg = render()
    assert svg.count(TRAIL_COLOR) == 1
    assert TRAIL_COLOR not in svg.split("prefers-color-scheme:dark)")[1]
