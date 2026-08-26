"""Card notation: losslessness, coverage, and palette drift.

These are the tests that stop a wrong algorithm reaching a printed card. They
are pure Python and run everywhere, including CI where Typst is absent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cubepath.algs import ALGORITHMS, DOT_SEQUENCE
from cubepath.cube import Cube, invert_algorithm
from cubepath.notation import (
    BIGCUBE_CHUNKS,
    CHUNKS,
    DOT_CHUNKS,
    PARITY_DIFF_4X4,
    PARITY_DIFF_5X5,
    PARITY_DIFF_INDEX,
    bigcube_algs,
    block_compactable,
    compact,
    compactable,
    expand,
    expand_key,
    tokenize,
)
from cubepath.palette import FAMILY, FAMILY_LABELS, TRIGGER_COLORS

_REPO = Path(__file__).resolve().parents[3]


# ── Losslessness ──────────────────────────────────────────────────────


@pytest.mark.parametrize("key", sorted(CHUNKS))
def test_chunks_round_trip_to_canonical(key: str) -> None:
    """What the card prints must expand back to the verified algorithm."""
    assert expand_key(key) == ALGORITHMS[key], f"{key} chunking is not lossless"


def test_dot_sequence_round_trips() -> None:
    assert expand(DOT_CHUNKS) == DOT_SEQUENCE


def test_every_canonical_algorithm_is_chunked() -> None:
    """Adding an algorithm fails the build until someone chunks it."""
    assert set(ALGORITHMS) - set(CHUNKS) == set()


def test_compaction_is_reversible_for_every_segment() -> None:
    for key, chunks in CHUNKS.items():
        for chunk in chunks:
            for seg in chunk:
                assert tokenize(compact(seg)) == tokenize(seg), f"{key}: {seg!r}"


# ── The compaction guard ──────────────────────────────────────────────


def test_layer_prefixed_algorithms_are_not_compactable() -> None:
    """`2R2 U2` compacted reads as either `2R2 U2` or `2R 2U2` — different
    cube states. The guard must refuse it."""
    assert compactable("R U R' U'")
    assert not compactable("2R2 U2 2R2 Uw2 2R2 Uw2")
    assert not compactable("Rw U2 3Rw' U2")
    with pytest.raises(ValueError):
        compact("2R2 U2")


def test_big_cube_block_stays_spaced() -> None:
    """One layer-prefixed algorithm spaces the whole block, so the gap never
    means two different things on one card."""
    assert not block_compactable(list(bigcube_algs().values()))


def test_tokenize_rejects_unparseable_text() -> None:
    with pytest.raises(ValueError):
        tokenize("R U QQQ R'")


# ── The new Phase-1 entries ───────────────────────────────────────────


@pytest.mark.parametrize(
    "key",
    ["Orient Corners Right", "Orient Corners Front", "Edge Insert Right", "Edge Insert Left"],
)
def test_phase1_finishers_are_valid_algorithms(key: str) -> None:
    alg = ALGORITHMS[key]
    cube = Cube.solved()
    cube.apply(alg)
    assert not cube.is_solved(), f"{key} does nothing"
    cube.apply(invert_algorithm(alg))
    assert cube.is_solved(), f"{key} does not invert cleanly"


def test_repeated_algorithms_are_stored_expanded() -> None:
    """No repeat operator in the data: `x2` would collide with the x rotation
    the 4x4 parity algorithm contains."""
    for key in ("Orient Corners Right", "Orient Corners Front"):
        tokens = tokenize(ALGORITHMS[key])
        assert tokens[: len(tokens) // 2] == tokens[len(tokens) // 2 :]


# ── Big cubes: the card must not drift from the verifiers ─────────────


def test_big_cube_algs_match_their_verified_sources() -> None:
    """Each string is read back out of the module that pins it for CI."""
    bc = bigcube_algs()
    extract = (_REPO / "app" / "scripts" / "extract-algs.mjs").read_text()
    l2e = (_REPO / "app" / "scripts" / "verify-l2e.mjs").read_text()
    assert f'"{bc["4x4-oll-parity"]}"' in extract
    assert f'"{bc["4x4-pll-parity"]}"' in extract
    assert f'"{bc["5x5-edge-parity"]}"' in l2e


def test_big_cube_chunks_round_trip() -> None:
    bc = bigcube_algs()
    for name, chunks in BIGCUBE_CHUNKS.items():
        assert expand(chunks) == bc[name], f"{name} chunking is not lossless"


def test_parity_algs_differ_by_exactly_one_token() -> None:
    """The card prints the two parity algorithms aligned so the single
    difference is visible; verify-l2e.mjs pins the same index."""
    bc = bigcube_algs()
    t4 = tokenize(bc["4x4-oll-parity"])
    t5 = tokenize(bc["5x5-edge-parity"])
    assert len(t4) == len(t5)
    diffs = [i for i, (a, b) in enumerate(zip(t4, t5)) if a != b]
    assert diffs == [PARITY_DIFF_INDEX]
    assert t4[PARITY_DIFF_INDEX] == PARITY_DIFF_4X4
    assert t5[PARITY_DIFF_INDEX] == PARITY_DIFF_5X5


# ── Colour is derived, never hand-assigned ────────────────────────────


def test_family_keys_are_canonical_token_strings() -> None:
    for key in FAMILY:
        assert " ".join(tokenize(key)) == key, f"{key!r} is not normalised"


def test_palette_matches_the_guide_filter() -> None:
    """One palette, defined once. The guide PDF and the card must agree."""
    lua = (_REPO / "guide" / "filters" / "callouts.lua").read_text()
    found = dict(re.findall(r'\["trig-(\w)"\] = \{ hex = "(\w{6})" \}', lua))
    assert found == TRIGGER_COLORS


def test_guide_trigger_spans_are_known_families() -> None:
    """Every coloured span in the guide is a family the card also knows, so
    the two teach one vocabulary."""
    md = (_REPO / "guide" / "cubepath.md").read_text()
    spans = re.findall(r"\[`?([^\]`]+)`?\]\{\.trig-(\w)\}", md)
    assert spans, "no trigger spans found — the guide's markup changed"
    for text, fam in spans:
        body = text.strip().strip("`")
        if body.lower() in FAMILY_LABELS:  # a family name, not a move string
            assert FAMILY_LABELS[body.lower()] == fam, f"label {body!r} in wrong family"
            continue
        tokens = " ".join(tokenize(body))
        assert FAMILY.get(tokens) == fam, f"guide span {tokens!r} is not family {fam!r}"
