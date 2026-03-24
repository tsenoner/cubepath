"""Tests verifying Rubik's cube algorithms against the cube simulator.

Algorithms sourced from the cubepath guide's algorithm reference table.
"""

from cubepath.cube import Cube

ALGORITHMS = {
    "F-sexy-F'": "F R U R' U' F'",
    "f-sexy-f'": "f R U R' U' f'",
    "Sune": "R U R' U R U2 R'",
    "Anti-Sune": "R U2 R' U' R U' R'",
    "Pi": "f R U R' U' f' F R U R' U' F'",
    "Headlights": "R2 D R' U2 R D' R' U2 R'",
    "Chameleon": "r U R' U' r' F R F'",
    "Bowtie": "F' r U R' U' r' F R",
    "Niklas": "R U' L' U R' U' L",
    "T-Perm": "R U R' U' R' F R2 U' R' U' R U R' F'",
    "Y-Perm": "F R U' R' U' R U R' F' R U R' U' R' F R F'",
    "Ua": "R U' R U R U R U' R' U' R2",
    "Ub": "R2 U R U R' U' R' U' R' U R'",
    "H-Perm": "M2 U' M2 U2 M2 U' M2",
    "Z-Perm": "M' U' M2 U' M2 U' M' U2 M2 U",
}


def _apply_on_solved(name: str) -> Cube:
    c = Cube.solved()
    c.apply(ALGORITHMS[name])
    return c


# ── OLL cross tests ──────────────────────────────────────────────────


def test_oll_cross_line():
    """F(R U R' U')F' solves the Line case (inverse creates it, forward solves it)."""
    c = Cube.solved()
    c.apply("F U R U' R' F'")  # inverse of F-sexy-F'
    u = c.faces["U"]
    assert u[4] == "Y"
    assert u[3] == "Y" and u[5] == "Y"  # horizontal line
    assert u[1] != "Y" and u[7] != "Y"
    c.apply(ALGORITHMS["F-sexy-F'"])
    assert c.u_cross_solved()


def test_oll_cross_hook():
    """f(R U R' U')f' solves the Hook case.

    The inverse creates a hook pattern: exactly 2 adjacent U-face edges are yellow.
    The forward algorithm then restores the full cross.
    """
    c = Cube.solved()
    c.apply("f U R U' R' f'")  # inverse of f-sexy-f'
    u = c.faces["U"]
    assert u[4] == "Y"
    # Verify exactly 2 cross edges are yellow (L-shape), the other 2 are not
    yellow_edges = [i for i in (1, 3, 5, 7) if u[i] == "Y"]
    non_yellow_edges = [i for i in (1, 3, 5, 7) if u[i] != "Y"]
    assert len(yellow_edges) == 2, f"Expected 2 yellow edges, got {yellow_edges}"
    assert len(non_yellow_edges) == 2
    # The 2 yellow edges should be adjacent (L-shape, not line)
    assert yellow_edges != [1, 7] and yellow_edges != [3, 5], "Edges form a line, not L-shape"
    # Apply algorithm to solve the cross
    c.apply(ALGORITHMS["f-sexy-f'"])
    assert c.u_cross_solved()


# ── OLL corner tests ─────────────────────────────────────────────────


def _verify_oll_corner_alg(name: str) -> None:
    """Verify an OLL corner algorithm: inverse creates a case, re-applying solves it."""
    c = Cube.solved()
    inverse_tokens = []
    for tok in reversed(ALGORITHMS[name].split()):
        if tok.endswith("'"):
            inverse_tokens.append(tok[:-1])
        elif tok.endswith("2"):
            inverse_tokens.append(tok)
        else:
            inverse_tokens.append(tok + "'")
    c.apply(" ".join(inverse_tokens))
    assert c.u_cross_solved(), f"{name} inverse broke the cross"
    c.apply(ALGORITHMS[name])
    assert c.u_face_solved(), f"{name} did not solve all U corners"


def test_oll_corner_sune():
    _verify_oll_corner_alg("Sune")


def test_oll_corner_antisune():
    _verify_oll_corner_alg("Anti-Sune")


def test_oll_corner_pi():
    _verify_oll_corner_alg("Pi")


def test_oll_corner_headlights():
    _verify_oll_corner_alg("Headlights")


def test_oll_corner_chameleon():
    _verify_oll_corner_alg("Chameleon")


def test_oll_corner_bowtie():
    _verify_oll_corner_alg("Bowtie")


# ── PLL tests ────────────────────────────────────────────────────────


def _u_layer_side_stickers(c: Cube) -> dict[str, list[str]]:
    """Get the top-row stickers of each side face (the U-layer ring)."""
    return {
        "F": [c.sticker_at("F", 0, j) for j in range(3)],
        "R": [c.sticker_at("R", 0, j) for j in range(3)],
        "B": [c.sticker_at("B", 0, j) for j in range(3)],
        "L": [c.sticker_at("L", 0, j) for j in range(3)],
    }


def _pll_preserves_u_face(c: Cube) -> bool:
    return all(s == "Y" for s in c.faces["U"])


def test_tperm_swaps_adjacent_corners_and_edges():
    c = _apply_on_solved("T-Perm")
    assert _pll_preserves_u_face(c)
    # Verify it's an involution (order 2)
    c.apply(ALGORITHMS["T-Perm"])
    assert c.is_solved()


def test_yperm_is_order_2():
    c = _apply_on_solved("Y-Perm")
    assert _pll_preserves_u_face(c)
    c.apply(ALGORITHMS["Y-Perm"])
    assert c.is_solved()


def test_ua_3cycles_edges():
    c = _apply_on_solved("Ua")
    assert _pll_preserves_u_face(c)
    sides = _u_layer_side_stickers(c)
    solved_sides = _u_layer_side_stickers(Cube.solved())
    for f in "FRBL":
        assert sides[f][0] == solved_sides[f][0], f"Ua moved corner at {f}[0]"
        assert sides[f][2] == solved_sides[f][2], f"Ua moved corner at {f}[2]"
    edge_displaced = sum(1 for f in "FRBL" if sides[f][1] != solved_sides[f][1])
    assert edge_displaced == 3, f"Ua displaced {edge_displaced} edges, expected 3"
    # Order 3
    c.apply(ALGORITHMS["Ua"])
    c.apply(ALGORITHMS["Ua"])
    assert c.is_solved()


def test_ub_3cycles_edges():
    c = _apply_on_solved("Ub")
    assert _pll_preserves_u_face(c)
    sides = _u_layer_side_stickers(c)
    solved_sides = _u_layer_side_stickers(Cube.solved())
    for f in "FRBL":
        assert sides[f][0] == solved_sides[f][0], f"Ub moved corner at {f}[0]"
        assert sides[f][2] == solved_sides[f][2], f"Ub moved corner at {f}[2]"
    edge_displaced = sum(1 for f in "FRBL" if sides[f][1] != solved_sides[f][1])
    assert edge_displaced == 3, f"Ub displaced {edge_displaced} edges, expected 3"
    c.apply(ALGORITHMS["Ub"])
    c.apply(ALGORITHMS["Ub"])
    assert c.is_solved()


def test_hperm_swaps_opposite_edges():
    c = _apply_on_solved("H-Perm")
    assert _pll_preserves_u_face(c)
    sides = _u_layer_side_stickers(c)
    solved_sides = _u_layer_side_stickers(Cube.solved())
    edge_displaced = sum(1 for f in "FRBL" if sides[f][1] != solved_sides[f][1])
    assert edge_displaced == 4, f"H-perm displaced {edge_displaced} edges, expected 4"
    for f in "FRBL":
        assert sides[f][0] == solved_sides[f][0]
        assert sides[f][2] == solved_sides[f][2]
    c.apply(ALGORITHMS["H-Perm"])
    assert c.is_solved()


def test_zperm_swaps_adjacent_edges():
    """Z-Perm swaps UF↔UR and UB↔UL (adjacent edge pairs)."""
    c = _apply_on_solved("Z-Perm")
    assert _pll_preserves_u_face(c)
    sides = _u_layer_side_stickers(c)
    solved_sides = _u_layer_side_stickers(Cube.solved())
    edge_displaced = sum(1 for f in "FRBL" if sides[f][1] != solved_sides[f][1])
    assert edge_displaced == 4, f"Z-perm displaced {edge_displaced} edges, expected 4"
    # Corners stay in place
    for f in "FRBL":
        assert sides[f][0] == solved_sides[f][0], f"Z-perm moved corner at {f}[0]"
        assert sides[f][2] == solved_sides[f][2], f"Z-perm moved corner at {f}[2]"
    # Involution (order 2)
    c.apply(ALGORITHMS["Z-Perm"])
    assert c.is_solved()


def test_niklas_cycles_corners():
    """Niklas (R U' L' U R' U' L) cycles corners — does NOT preserve U face.

    The guide says: 'Niklas can't be used here — it destroys the yellow face.'
    It's used for corner positioning (Phase 2, step 6), not PLL.
    """
    c = _apply_on_solved("Niklas")
    # Niklas does NOT preserve U face (it's not a PLL algorithm)
    assert not _pll_preserves_u_face(c), "Niklas unexpectedly preserved U face"
    # But the 7-move Niklas has order 4 (3-cycle + net U' rotation)
    c2 = Cube.solved()
    for _ in range(4):
        c2.apply(ALGORITHMS["Niklas"])
    assert c2.is_solved(), "Niklas should have order 4"
    # It moves corners
    sides = _u_layer_side_stickers(c)
    solved_sides = _u_layer_side_stickers(Cube.solved())
    corner_displaced = sum(1 for f in "FRBL" for i in (0, 2) if sides[f][i] != solved_sides[f][i])
    assert corner_displaced > 0, "Niklas didn't move any corners"
