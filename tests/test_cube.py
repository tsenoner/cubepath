"""Tests for the cube simulator — validates correctness before using it elsewhere."""

from cubepath.cube import Cube, parse_algorithm


def test_solved_is_solved():
    assert Cube.solved().is_solved()


def test_single_move_not_solved():
    c = Cube.solved()
    c.apply_move("R")
    assert not c.is_solved()


def test_move_inverse_restores():
    """R then R' = identity, for all base moves."""
    for move in ["R", "L", "U", "D", "F", "B", "M", "S", "E"]:
        c = Cube.solved()
        c.apply_move(move)
        c.apply_move(move + "'")
        assert c.is_solved(), f"{move} {move}' did not restore solved"


def test_move_4x_identity():
    """Any base move applied 4 times = identity."""
    for move in ["R", "L", "U", "D", "F", "B", "M", "S", "E"]:
        c = Cube.solved()
        for _ in range(4):
            c.apply_move(move)
        assert c.is_solved(), f"{move}×4 ≠ identity"


def test_double_equals_2x():
    """R2 equals R applied twice."""
    for move in ["R", "L", "U", "D", "F", "B"]:
        c1 = Cube.solved()
        c1.apply_move(move + "2")
        c2 = Cube.solved()
        c2.apply_move(move)
        c2.apply_move(move)
        assert c1.faces == c2.faces, f"{move}2 ≠ {move}×2"


def test_wide_r_equals_r_plus_m_prime():
    c1 = Cube.solved()
    c1.apply_move("r")
    c2 = Cube.solved()
    c2.apply_move("R")
    c2.apply_move("M'")
    assert c1.faces == c2.faces


def test_xyz_rotation_4x_identity():
    for rot in ["x", "y", "z"]:
        c = Cube.solved()
        for _ in range(4):
            c.apply_move(rot)
        assert c.is_solved(), f"{rot}×4 ≠ identity"


def test_sexy_move_6x_identity():
    """(R U R' U')×6 = identity."""
    c = Cube.solved()
    for _ in range(6):
        c.apply("R U R' U'")
    assert c.is_solved()


def test_tperm_squared_identity():
    """T-perm is an involution (order 2)."""
    tperm = "R U R' U' R' F R2 U' R' U' R U R' F'"
    c = Cube.solved()
    c.apply(tperm)
    assert not c.is_solved()
    c.apply(tperm)
    assert c.is_solved()


def test_sune_6x_identity():
    """Sune has order 6."""
    sune = "R U R' U R U2 R'"
    c = Cube.solved()
    for _ in range(6):
        c.apply(sune)
    assert c.is_solved()


def test_parse_simple():
    assert parse_algorithm("R U R' U'") == ["R", "U", "R'", "U'"]


def test_parse_double():
    assert parse_algorithm("R2 U2") == ["R2", "U2"]


def test_parse_wide():
    assert parse_algorithm("r U R'") == ["r", "U", "R'"]


def test_parse_parenthesized_repeat():
    assert parse_algorithm("(R U)×2") == ["R", "U", "R", "U"]


def test_compound_wide_moves():
    """Wide f = F + S."""
    c1 = Cube.solved()
    c1.apply_move("f")
    c2 = Cube.solved()
    c2.apply("F S")
    assert c1.faces == c2.faces


def test_compound_rotations():
    """x = R + M' + L', y = U + E' + D', z = F + S + B'."""
    for rot, decomp in [("x", "R M' L'"), ("y", "U E' D'"), ("z", "F S B'")]:
        c1 = Cube.solved()
        c1.apply_move(rot)
        c2 = Cube.solved()
        c2.apply(decomp)
        assert c1.faces == c2.faces, f"{rot} ≠ {decomp}"


def test_superflip_order():
    """Superflip has a known high order — just verify it's not identity after 1 application."""
    c = Cube.solved()
    c.apply("U R2 F B R B2 R U2 L B2 R U' D' R2 F R' L B2 U2 F2")
    assert not c.is_solved()
