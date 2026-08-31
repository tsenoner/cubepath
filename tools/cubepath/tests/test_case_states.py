"""The cross-language seam: case-states.json against Python's own cube model.

`app/scripts/gen-case-states.mjs` derives every case's facelet state from the
cubing.js kpuzzle and writes it to `app/src/data/extracted/case-states.json`.
Python reads that file and draws from it — for 4x4 and 5x5 it has no choice,
because `cube.py` is a gated 3x3 mirror and refuses big-cube notation.

That makes the JSON a contract between two cube models that were never
compared. This module compares them. For every 3x3 case that exists on both
sides, the state cube.py computes and the state cubing.js exported must agree
facelet for facelet, in the same orientation, with no fudge factor. 119 cases
(57 OLL + 21 PLL + 41 F2L) x 54 facelets is the evidence that the big-cube
states — which Python cannot check — come from a model that agrees with it
everywhere it can be checked.

A failure here is a real finding about one of the two models, never a reason
to relax the comparison.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

import pytest

from cubepath.cube import COLORS, Cube
from cubepath.fullsets import _ROTATIONS, case_state

_REPO = Path(__file__).resolve().parents[3]
_STATES = _REPO / "app" / "src" / "data" / "extracted" / "case-states.json"
_JPERM = _REPO / "app" / "src" / "data" / "extracted" / "jperm-raw.json"
_F2L = _REPO / "app" / "src" / "data" / "extracted" / "f2l-raw.json"

# cube.py names stickers by colour letter; the JSON names them by face letter,
# because cubing.js uses a different palette for the same six faces. This is
# the only place the two vocabularies meet, and it is just COLORS inverted.
_FACE_OF_COLOR = {color: face for face, color in COLORS.items()}

_MASK_CHARS = set(".ox")


@functools.cache
def _states() -> dict[str, Any]:
    if not _STATES.exists():
        raise AssertionError(f"{_STATES} is missing — run `node scripts/gen-case-states.mjs`")
    data: dict[str, Any] = json.loads(_STATES.read_text())
    return data


@functools.cache
def _by_id() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in _states()["cases"]}


def _python_faces(cube: Cube) -> dict[str, str]:
    """cube.py's six faces in the JSON's vocabulary: face letters, row-major."""
    return {face: "".join(_FACE_OF_COLOR[s] for s in cube.faces[face]) for face in COLORS}


def _centers_home(cube: Cube) -> bool:
    return all(cube.faces[f][4] == COLORS[f] for f in COLORS)


def _setup_state(setup: str) -> Cube:
    """The state a pinned F2L setup produces, rotated until centres are home.

    Mirrors `setupState` in gen-case-states.mjs: a forward state carries any net
    rotation on the RIGHT, so the cancelling rotation is applied afterwards.
    """
    base = Cube.solved()
    base.apply(setup)
    for rot in _ROTATIONS:
        c = base.copy()
        if rot:
            c.apply(rot)
        if _centers_home(c):
            return c
    raise AssertionError(f"no rotation brings centres home for setup {setup!r}")


# ── Shape of the contract ─────────────────────────────────────────────


def test_schema_and_layouts_are_well_formed() -> None:
    data = _states()
    assert data["schema"] == 1
    assert data["faces"] == ["U", "L", "F", "R", "B", "D"]
    assert set(data["faceColors"]) == set(data["faces"])
    # The palette the JSON declares is cube.py's palette, spelled out.
    assert {f: c[0] for f, c in data["faceColors"].items()} == COLORS
    assert set(data["maskLegend"]) == _MASK_CHARS
    for puzzle, layout in data["layouts"].items():
        n = layout["n"]
        assert n == int(puzzle[0]), puzzle
        addresses = [a for face in data["faces"] for a in layout["facelets"][face]]
        assert len(addresses) == 6 * n * n, puzzle
        orbits = {o["name"]: o for o in layout["orbits"]}
        for address in addresses:
            orbit, slot, ori = address.split(":")
            assert orbit in orbits, address
            assert 0 <= int(slot) < orbits[orbit]["numPieces"], address
            assert 0 <= int(ori) < orbits[orbit]["numOrientations"], address


def test_every_case_is_a_legal_colouring() -> None:
    """Whatever the puzzle size, a state must have n*n stickers of each face."""
    data = _states()
    for case in data["cases"]:
        n = data["layouts"][case["puzzle"]]["n"]
        counts = dict.fromkeys(data["faces"], 0)
        for face in data["faces"]:
            state = case["state"][face]
            mask = case["mask"][face]
            assert len(state) == n * n, case["id"]
            assert len(mask) == n * n, case["id"]
            assert set(mask) <= _MASK_CHARS, case["id"]
            for ch in state:
                assert ch in counts, f"{case['id']}: unknown face letter {ch!r}"
                counts[ch] += 1
        assert set(counts.values()) == {n * n}, f"{case['id']}: {counts}"


def test_case_ids_cover_the_extracted_sets_exactly() -> None:
    """No case silently dropped, none invented."""
    jperm = json.loads(_JPERM.read_text())
    f2l = json.loads(_F2L.read_text())
    expected = {
        "oll": len(jperm["oll"]),
        "pll": len(jperm["pll"]),
        "f2l": len(f2l["f2l"]),
        "4x4oll": len(jperm["4x4oll"]),
        "4x4pll": len(jperm["4x4pll"]),
        "555l2e": 13,
        # The course's own OLL-parity picture. Not one of the 27: every case in
        # JPerm's 4x4 OLL set has parity spliced into a last-layer algorithm,
        # so none of them is bare parity, and `444.oll-parity` had no state.
        "4x4parity": 1,
    }
    got: dict[str, int] = {}
    for case in _states()["cases"]:
        got[case["set"]] = got.get(case["set"], 0) + 1
    assert got == expected
    ids = [c["id"] for c in _states()["cases"]]
    assert len(ids) == len(set(ids))


def _rows(state: str, n: int) -> list[str]:
    return [state[r * n : (r + 1) * n] for r in range(n)]


# The four last-layer sets. F2L is excluded (its case lives in the FR slot, one
# layer down) and 555l2e is excluded on purpose — see below.
_LAST_LAYER_SETS = ("oll", "pll", "4x4oll", "4x4pll")


def test_last_layer_sets_disturb_only_the_last_layer() -> None:
    """The strongest check available for the 4x4 states Python cannot model.

    An OLL/PLL case, at any cube size, is F2L-solved with the case confined to
    the top layer. If the export's orientation, its rotation normalisation or
    its facelet grid were wrong for the 4x4, this would not hold for 49 cases
    at once.
    """
    data = _states()
    for case in data["cases"]:
        if case["set"] not in _LAST_LAYER_SETS:
            continue
        n = data["layouts"][case["puzzle"]]["n"]
        assert set(case["state"]["D"]) == {"D"}, f"{case['id']}: D face not solved"
        for face in ("L", "F", "R", "B"):
            for row in _rows(case["state"][face], n)[1:]:
                assert set(row) == {face}, f"{case['id']}: {face} disturbed below the top row"


def test_permutation_sets_are_fully_oriented() -> None:
    """A PLL case is oriented by definition — at 3x3 and at 4x4 alike."""
    for case in _states()["cases"]:
        if case["set"] in ("pll", "4x4pll"):
            assert set(case["state"]["U"]) == {"U"}, case["id"]


def test_the_5x5_l2e_states_are_the_displayed_hold() -> None:
    """L2E states are the hold a solver sees, not `alg⁻¹`.

    This used to assert the opposite — that the set was exported RAW and
    flagged undrawable, because an L2E algorithm is held partway through
    reduction and its raw case state does not present at UF/UB. verify-l2e.mjs
    now exports the displayed pattern its own check (d) already round-trips,
    so the set is drawable and this test pins what makes it drawable: the case
    is confined to the two target groups and everything else is solved in
    place. A regression here would draw thirteen plausible pictures of the
    wrong cube.
    """
    l2e = [c for c in _states()["cases"] if c["set"] == "555l2e"]
    assert len(l2e) == 13
    n = _states()["layouts"]["5x5x5"]["n"]
    # The two target groups, as facelet positions: UF is U's last row and F's
    # top row, UB is U's first row and B's top row — the middle n-2 cells of
    # each, which is the group and not the corners beside it.
    middles = range(1, n - 1)
    allowed = {("U", i) for i in middles} | {("U", n * (n - 1) + i) for i in middles}
    allowed |= {("F", i) for i in middles} | {("B", i) for i in middles}
    for case in l2e:
        assert case["derivation"] == "displayed", case["id"]
        assert case["preRotation"] == "", case["id"]
        off_target = {
            (face, i)
            for face, mask in case["mask"].items()
            for i, ch in enumerate(mask)
            if ch != "."
            if (face, i) not in allowed
        }
        assert not off_target, f"{case['id']}: case content outside UF/UB at {sorted(off_target)}"


# ── The cross-check: two independent cube models, one answer ──────────


def _three_by_three_cases() -> list[tuple[str, Cube]]:
    """Every exported 3x3 case, with the state cube.py derives for it."""
    out = []
    for case in _states()["cases"]:
        if case["puzzle"] != "3x3x3":
            continue
        if case["derivation"] == "setup":
            out.append((case["id"], _setup_state(case["alg"])))
        else:
            out.append((case["id"], case_state(case["alg"])))
    return out


_CROSS_CHECK = _three_by_three_cases()


def test_the_cross_check_covers_every_three_by_three_case() -> None:
    """A silently-shrinking comparison would make the gate meaningless."""
    assert len(_CROSS_CHECK) == sum(1 for c in _states()["cases"] if c["puzzle"] == "3x3x3")
    assert len(_CROSS_CHECK) == 119, "57 OLL + 21 PLL + 41 F2L"


@pytest.mark.parametrize(("case_id", "cube"), _CROSS_CHECK, ids=[c[0] for c in _CROSS_CHECK])
def test_python_and_kpuzzle_agree_on_every_3x3_case(case_id: str, cube: Cube) -> None:
    """cube.py's state and cubing.js's exported state, facelet for facelet."""
    exported = _by_id()[case_id]["state"]
    assert _python_faces(cube) == exported, case_id


@pytest.mark.parametrize(("case_id", "cube"), _CROSS_CHECK, ids=[c[0] for c in _CROSS_CHECK])
def test_python_and_kpuzzle_agree_on_which_facelets_are_solved(case_id: str, cube: Cube) -> None:
    """The mask is piece-level, so Python can only check its coarse claim: a
    facelet marked solved must show its own face's colour."""
    case = _by_id()[case_id]
    faces = _python_faces(cube)
    for face in _states()["faces"]:
        for i, (mask, sticker) in enumerate(zip(case["mask"][face], faces[face], strict=True)):
            if mask == ".":
                assert sticker == face, f"{case_id}: {face}[{i}] marked solved but shows {sticker}"


# ── Parity algorithms: the export that replaced the JS regex-scrape ───


def test_parity_algs_are_exported_and_consistent() -> None:
    from cubepath.notation import bigcube_algs, tokenize

    parity = _states()["parityAlgs"]
    # "edge-flip" is not a parity algorithm; it rides in the same map because
    # it is the same kind of thing to Python — a big-cube string the card must
    # print without retyping. Its source is a script path, not a JSON index.
    assert set(parity) == {
        "4x4-oll-parity",
        "4x4-pll-parity",
        "5x5-edge-parity",
        "edge-flip",
    }
    for key, entry in parity.items():
        assert entry["alg"].strip(), key
        assert entry["source"].endswith("]") or key == "edge-flip", key
        assert entry["signature"], key
    # notation.py must now be reading these, not scraping JavaScript source.
    printed = bigcube_algs()
    # The card's table keys the flip by its role in the deck ("l2e-flip");
    # case-states keys it by what it is ("edge-flip"). One rename, written down.
    CARD_KEY = {"edge-flip": "l2e-flip"}
    for key, entry in parity.items():
        assert printed[CARD_KEY.get(key, key)] == entry["alg"], key
    t4 = tokenize(parity["4x4-oll-parity"]["alg"])
    t5 = tokenize(parity["5x5-edge-parity"]["alg"])
    assert len(t4) == len(t5)
    assert sum(1 for a, b in zip(t4, t5, strict=True) if a != b) == 1


def test_notation_no_longer_parses_javascript_source() -> None:
    """The seam this file exists to close: Python reads JSON, not JS text.

    Checked against the module's source because the failure mode is a silent
    regression — a new constant scraped out of a fifth JS file would still
    produce the right string today and break on the next rename.
    """
    import cubepath.notation as notation

    source = Path(notation.__file__).read_text()
    assert "_js_const" not in source
    # notation.py addresses `app/src/data/extracted/`, never `app/scripts/`.
    assert '"scripts"' not in source
    # _L2E_DATA went away when the edge flip started arriving through
    # case-states.json like the parity algorithms — one JS→Python boundary,
    # not two. The invariant is unchanged: every path here is JSON data.
    for path in (notation._CASE_STATES, notation._JPERM):
        assert path.suffix == ".json", path
