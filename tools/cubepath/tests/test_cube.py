"""Tests for the cube simulator — validates correctness before using it elsewhere."""

import pytest

from cubepath.algs import ALGORITHMS, DOT_SEQUENCE
from cubepath.cube import (
    Cube,
    UnsupportedNotationError,
    UnsupportedPuzzleError,
    invert_algorithm,
    parse_algorithm,
)
from cubepath.notation import bigcube_algs, pll_algs


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


def test_parse_multiple_repeat_groups():
    assert parse_algorithm("(R U)×2 (L D)×2") == ["R", "U", "R", "U", "L", "D", "L", "D"]


def test_parse_visual_group_without_repeat():
    """A "(…)" with no ×N is visual grouping — its moves must not be dropped."""
    assert parse_algorithm("(R U) L") == ["R", "U", "L"]


def test_parse_visual_groups_keep_all_moves_in_order():
    """A later "(" must not discard an earlier unrepeated group (old flush bug)."""
    assert parse_algorithm("(r U r') U R U' R' (r U' r')") == [
        "r",
        "U",
        "r'",
        "U",
        "R",
        "U'",
        "R'",
        "r",
        "U'",
        "r'",
    ]


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


# ── Scope gate: this is a 3x3 simulator and must say so out loud ──────
#
# cube.py used to accept a 4x4 algorithm and return a confident, meaningless
# 3x3 state: `_TOKEN_RE.findall` dropped whatever it could not match, so `3Rw`
# became `r`, `2R2` became `R2` and `m'` vanished. Everything below pins the
# refusal, because the failure mode it replaces — a plausible-looking wrong
# picture — is the one this repo can least afford.


BIG_CUBE_PARITY = "r U2 x r U2 r U2 r' U2 l U2 r' U2 r U2 r' U2 r'"
"""The standard 4x4 OLL-parity algorithm, transcribed into lowercase wide
moves. Every token is legal 3x3 notation, so nothing in the *string* betrays
it — the only honest defence is for the caller to declare the puzzle."""


def test_declaring_a_big_cube_raises_rather_than_answering():
    """The 4x4 parity alg is token-for-token legal on a 3x3, so it can only be
    refused by the size the caller declares. Refuse it there, loudly."""
    with pytest.raises(UnsupportedPuzzleError) as exc:
        parse_algorithm(BIG_CUBE_PARITY, size=4)
    assert "size=4" in str(exc.value)
    assert "kpuzzle" in str(exc.value), "the message must point at the real source of truth"


@pytest.mark.parametrize("size", [2, 4, 5, 7])
def test_no_cube_can_be_built_at_any_other_size(size):
    """There is no size at which this class does something else, so there is no
    size at which it should hand back an answer."""
    with pytest.raises(UnsupportedPuzzleError):
        Cube.solved(size=size)
    with pytest.raises(UnsupportedPuzzleError):
        Cube(faces={}, size=size)


@pytest.mark.parametrize("name", sorted(bigcube_algs()))
def test_every_big_cube_string_the_repo_stores_is_refused(name):
    """The four big-cube algorithms this repo actually keeps — read from the
    modules that pin them for CI, never retyped — must all bounce, even with
    no size declared, because every one of them is written in notation a 3x3
    cannot express."""
    alg = bigcube_algs()[name]
    with pytest.raises(UnsupportedNotationError) as exc:
        Cube.solved().apply(alg)
    offender = next(t for t in alg.split() if t.rstrip("2'")[0].isdigit() or "w" in t.rstrip("2'"))
    assert offender in str(exc.value), (
        f"the error must name the token that caused it; {offender!r} missing from {exc.value}"
    )


@pytest.mark.parametrize(
    "alg,offender",
    [
        ("Rw U2 3Rw U2 3Rw2 F2", "3Rw"),  # was silently truncated to `r`
        ("2R2 U2 2R2 Uw2 2R2 Uw2", "2R2"),  # inner slice was read as an outer turn
        ("m' U' m2 U' m2", "m'"),  # wing slice vanished token by token
        ("y2 R' U R' U' R3 U' R2", "R3"),  # triple turn was read as a single
        ("(R' F R F')2", "F')2"),  # postfix repeat count was dropped
        ("R U QQQ R'", "QQQ"),  # plain junk
    ],
)
def test_unmodellable_tokens_raise_and_name_themselves(alg, offender):
    """Whoever trips this later needs to know which token did it."""
    with pytest.raises(UnsupportedNotationError) as exc:
        parse_algorithm(alg)
    assert offender in str(exc.value), f"{offender!r} not named in: {exc.value}"


def test_a_stray_repeat_count_raises_instead_of_disappearing():
    with pytest.raises(UnsupportedNotationError):
        parse_algorithm("R U ×2")


# ── ...and the precision half: real 3x3 notation must keep working ────


@pytest.mark.parametrize("wide", ["r", "l", "u", "d", "f", "b"])
def test_lowercase_wide_moves_stay_legal(wide):
    """Bare lowercase wide moves are legitimate 3x3 notation and the repo's own
    algorithms use them (`f R U R' U' f'`, `r U R' U' r' F R F'`). The
    big-cube refusal targets the SiGN spelling `Rw`, which the 3x3 corpus never
    uses; it must not catch these."""
    assert parse_algorithm(f"{wide} U {wide}' U2 {wide}2") == [
        wide,
        "U",
        f"{wide}'",
        "U2",
        f"{wide}2",
    ]
    c = Cube.solved()
    c.apply_move(wide)
    assert not c.is_solved()


def _repo_3x3_algorithms() -> dict[str, str]:
    """Every 3x3 algorithm the repo owns, from its canonical modules."""
    algs = dict(ALGORITHMS)
    algs["Dot sequence"] = DOT_SEQUENCE
    algs.update({f"PLL {name}": alg for name, alg in pll_algs().items()})
    return algs


def test_the_repo_owns_enough_3x3_algorithms_for_this_gate_to_mean_something():
    assert len(_repo_3x3_algorithms()) >= 43, "this gate stopped seeing the algorithm set"


@pytest.mark.parametrize("name", sorted(_repo_3x3_algorithms()))
def test_every_repo_3x3_algorithm_still_simulates(name):
    """The refusal must be precise, not blunt: nothing the repo actually
    teaches may be caught by it."""
    alg = _repo_3x3_algorithms()[name]
    tokens = parse_algorithm(alg)
    assert tokens, f"{name} parsed to nothing"
    c = Cube.solved()
    c.apply(alg)
    assert not c.is_solved(), f"{name} does nothing"
    c.apply(invert_algorithm(alg))
    assert c.is_solved(), f"{name} does not invert cleanly"


def test_no_repo_3x3_algorithm_uses_sign_notation():
    """The measurement the SiGN refusal rests on. If a 3x3 algorithm ever
    arrives written `Rw`, this fails first and explains why the parser will."""
    offenders = {
        name: alg
        for name, alg in _repo_3x3_algorithms().items()
        if any("w" in t or t[0].isdigit() for t in alg.split())
    }
    assert not offenders, f"3x3 algorithms written in big-cube notation: {offenders}"
