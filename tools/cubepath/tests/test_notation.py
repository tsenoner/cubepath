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
    PLL_CHUNKS,
    PLL_OWNED,
    bigcube_algs,
    block_compactable,
    chunk_boundaries,
    compact,
    compactable,
    expand,
    expand_key,
    family,
    normalize,
    pll_algs,
    pll_rows,
    tokenize,
)
from cubepath.palette import (
    CALLOUTS,
    DARK_TRIGGER_COLORS,
    FAMILY,
    FAMILY_LABELS,
    SCREEN_TRIGGER_COLORS,
    TRIGGER_COLORS,
    contrast,
    print_tint,
)

_REPO = Path(__file__).resolve().parents[3]
_LUA = _REPO / "guide" / "filters" / "callouts.lua"
_TOKENS = _REPO / "app" / "src" / "styles" / "tokens.css"
_CALLOUT_ASTRO = _REPO / "app" / "src" / "components" / "Callout.astro"
_ALGTEXT_ASTRO = _REPO / "app" / "src" / "components" / "AlgText.astro"


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
    # The flip is the one card string with no case of its own to be looked up
    # in, so this is the only thing tying the printed string to the verifier
    # that proves it is outer-turns-only and legal on both big cubes. Without
    # it the card could quietly print a different algorithm under a cue —
    # "slice out, run it, slice back -- both cubes" — that is only true of
    # this one. It printed l2e-1 for exactly that reason until 2026-08-28.
    assert f'const EDGE_FLIP = "{bc["l2e-flip"]}";' in l2e, (
        "the card's flip string is not the one verify-l2e.mjs pins"
    )


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


# ── One palette, three renderings ─────────────────────────────────────
# palette.py declares the colours; guide/filters/callouts.lua draws them on
# paper and app/src/{styles/tokens.css,components/*.astro} draws them on
# screen. None of the three can import either of the others, so the rule the
# repo already applies to the trigger triad — a duplicated value is pinned by
# a test — is applied here to every value they share.


def _lua_callouts() -> dict[str, dict[str, str]]:
    """The `callout_styles` table, as the guide filter actually spells it."""
    lua = _LUA.read_text()
    table = lua[lua.index("local callout_styles = {") : lua.index("\nlocal trigger_colors")]
    entries = re.findall(r"\n  (\w+) = \{(.*?)\n  \},", table, re.S)
    assert entries, "callout_styles no longer parses — the filter's shape changed"
    return {name: dict(re.findall(r'(\w+) = "([^"]+)"', body)) for name, body in entries}


def _css_tokens(scope: str) -> dict[str, str]:
    """Custom properties declared in one theme block of tokens.css.

    `scope` is "light" (the :root palette, everything above the dark block),
    "dark" (the [data-theme="dark"] override the toggle sets) or "media" (the
    prefers-color-scheme copy). The app hand-duplicates the last two, so the
    tests below check the pair rather than trusting one of them.
    """
    css = _TOKENS.read_text()
    anchors = {
        "light": ("/* Cubepath design tokens", '[data-theme="dark"]'),
        "dark": ('[data-theme="dark"] {', "\n}"),
        "media": (':root:not([data-theme="light"])', "\n  }"),
    }
    open_at, close = anchors[scope]
    start = css.index(open_at)
    block = css[start : css.index(close, start + len(open_at))]
    found = dict(re.findall(r"(--[\w-]+):\s*([^;]+);", block))
    assert found, f"no tokens parsed from the {scope} block"
    return found


def test_palette_matches_the_guide_filter() -> None:
    """One palette, defined once. The guide PDF and the card must agree."""
    lua = _LUA.read_text()
    found = dict(re.findall(r'\["trig-(\w)"\] = \{ hex = "(\w{6})" \}', lua))
    assert found == TRIGGER_COLORS


def test_screen_triads_match_the_app_tokens() -> None:
    """The screen counterparts are declared in palette.py so the print
    deviation is a relation between two named triads, not a docstring. That
    only holds while the names still describe what the app ships."""
    for scope, expected in (
        ("light", SCREEN_TRIGGER_COLORS),
        ("dark", DARK_TRIGGER_COLORS),
        ("media", DARK_TRIGGER_COLORS),
    ):
        tokens = _css_tokens(scope)
        found = {k: tokens[f"--trig-{k}"].lstrip("#").upper() for k in expected}
        assert found == expected, f"tokens.css {scope} --trig-* drifted from palette.py"


def test_print_triad_is_darker_than_the_screen_triad() -> None:
    """The one licensed fork in the trigger palette, asserted in both
    directions: print is darker than screen for every family (not just on
    average), and clears 7:1 on white so it out-weighs nothing it sits beside
    on a mono laser. Delete this and "deliberately darkened" becomes a claim
    no one can check."""
    for fam, print_hex in TRIGGER_COLORS.items():
        screen_hex = SCREEN_TRIGGER_COLORS[fam]
        assert contrast(print_hex, "FFFFFF") > contrast(screen_hex, "FFFFFF"), (
            f"family {fam}: the print hex is no longer darker than the screen hex"
        )
        assert contrast(print_hex, "FFFFFF") >= 7.0, f"family {fam} faded on paper"


def test_app_trigger_families_match_the_palette() -> None:
    """`palette.FAMILY` says colour is never hand-assigned. AlgText.astro held
    4 of these 10, so six families — every mirror and wide-grip sexy move —
    were coloured on paper and plain in the app."""
    src = _ALGTEXT_ASTRO.read_text()
    table = src[src.index("const FAMILY: Record") : src.index("\n};", src.index("const FAMILY"))]
    found = dict(re.findall(r'"([^"]+)": "(\w)"', table))
    assert found == FAMILY


def test_callout_palette_matches_the_guide_filter() -> None:
    """Same four callouts, same anatomy, one definition. `ink` is the rule and
    the label both — the guide's old Material 500 borders measured 2.16-3.12:1
    on white and answered to no token on either side."""
    found = _lua_callouts()
    assert set(found) == set(CALLOUTS)
    for name, style in CALLOUTS.items():
        assert found[name] == {
            "label": style.label,
            "bg": print_tint(style),
            "ink": style.ink,
        }, f"callouts.lua .{name} drifted from palette.CALLOUTS"


def test_callout_palette_matches_the_app_tokens() -> None:
    """Every callout hex in palette.py names the tokens.css property it
    mirrors; resolve the names against the real stylesheet. This is the seam
    that had drifted furthest — the app retuned --warn to #b23c00 in a
    contrast audit and the guide kept printing E65100 at 3.46:1 on its tint."""
    light = _css_tokens("light")
    for name, style in CALLOUTS.items():
        assert light[style.tint_token].lstrip("#").upper() == style.tint, f".{name} tint"
        assert light[style.ink_token].lstrip("#").upper() == style.ink, f".{name} ink"


def test_app_callout_uses_the_token_pair_it_declares() -> None:
    """Callout.astro must reach its colours through the two tokens palette.py
    names, and must draw the rule and the label with the same one."""
    css = _CALLOUT_ASTRO.read_text()
    declared = re.search(r"const LABELS = \{([^}]*)\}", css)
    assert declared, "Callout.astro LABELS no longer parses"
    labels = dict(re.findall(r'(\w+): "([^"]+)"', declared.group(1)))
    assert labels == {name: style.label for name, style in CALLOUTS.items()}
    for name, style in CALLOUTS.items():
        surface = re.search(
            rf"\.{name} \{{\s*background: var\((--[\w-]+)\);\s*border-color: var\((--[\w-]+)\);",
            css,
        )
        label = re.search(rf"\.{name} \.label \{{\s*color: var\((--[\w-]+)\);", css)
        assert surface and label, f"Callout.astro .{name} no longer parses"
        assert surface.group(1) == style.tint_token, f".{name} tint token"
        assert surface.group(2) == label.group(1) == style.ink_token, f".{name} ink token"


def test_only_the_recessed_surface_forks_between_print_and_screen() -> None:
    """The second licensed deviation. `--card` is the app's *lift* off an
    off-white --paper; the guide prints on pure white, where a lift does not
    exist, so that one surface recesses instead. Every other callout colour is
    identical on both sides — assert that, so a third fork cannot be slipped
    in as a fourth colour tweak."""
    light = _css_tokens("light")
    forked = {n for n, s in CALLOUTS.items() if print_tint(s) != s.tint}
    assert forked == {"info"}, f"unlicensed print/screen fork: {forked - {'info'}}"
    card, paper = light["--card"], light["--paper"]
    assert contrast(card, "000000") > contrast(paper, "000000"), (
        "--card no longer lifts off --paper"
    )
    assert contrast(print_tint(CALLOUTS["info"]), "FFFFFF") > 1.0, "the print tint vanished"


def test_dark_theme_blocks_agree_on_every_callout_token() -> None:
    """tokens.css writes the dark palette twice — [data-theme] and the media
    query — so the callouts these tests pin are only pinned in one theme
    unless the two copies agree."""
    dark, media = _css_tokens("dark"), _css_tokens("media")
    shared = {t for s in CALLOUTS.values() for t in (s.tint_token, s.ink_token)}
    shared |= {f"--trig-{k}" for k in TRIGGER_COLORS}
    for token in sorted(shared):
        assert dark[token] == media[token], f"{token} differs between the two dark blocks"


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


# ── PLL: the 21 cases Card 3 prints ───────────────────────────────────


@pytest.mark.parametrize("name", [r.name for r in pll_rows()])
def test_pll_chunks_round_trip(name: str) -> None:
    """Card 3's chunking must expand back to the algorithm, character for
    character. This is the gate that lets the card compact and colour a
    17-move alg without ever becoming a retyped copy of it."""
    assert expand(PLL_CHUNKS[name]) == pll_algs()[name], f"{name} chunking is not lossless"


def test_pll_covers_all_21_in_source_order() -> None:
    assert list(PLL_CHUNKS) == [r.name for r in pll_rows()]
    assert len(PLL_CHUNKS) == 21


def test_owned_pll_cases_print_the_guide_string() -> None:
    """The six cases the guide teaches print what the learner already drilled,
    not JPerm's. Three of the six genuinely differ, so this is not a tie."""
    algs = pll_algs()
    for name, key in PLL_OWNED.items():
        assert algs[name] == ALGORITHMS[key]
        assert PLL_CHUNKS[name] is CHUNKS[key]
    differ = {n for n, k in PLL_OWNED.items() if algs[n] != _jperm_primary(n)}
    assert differ == {"Ub", "H", "Z"}, f"guide/JPerm divergence moved: {differ}"


def _jperm_primary(name: str) -> str:
    import json

    from cubepath.notation import _JPERM

    for case in json.loads(_JPERM.read_text())["pll"]:
        if case["name"] == name:
            return normalize(case["algs"][0])
    raise AssertionError(f"no PLL case named {name}")


def test_pll_sources_are_tagged_and_exhaustive() -> None:
    rows = pll_rows()
    assert {r.source for r in rows} == {"algs.py", "jperm-raw"}
    assert sum(r.source == "algs.py" for r in rows) == len(PLL_OWNED) == 6
    assert {r.group for r in rows} == {
        "Edges Only",
        "Adjacent Corner Swap",
        "Diagonal Corner Swap",
    }


def test_normalize_drops_only_parentheses_and_spacing() -> None:
    assert normalize("R' (U R U' R') F'") == "R' U R U' R' F'"
    assert normalize("R2  U   R'") == "R2 U R'"
    # No token is welded to its neighbour when a parenthesis is removed.
    for row in pll_rows():
        assert tokenize(row.alg) == row.alg.split()


def test_jperm_execution_units_survive_as_chunk_boundaries() -> None:
    """JPerm marks execution units with parentheses — `(U' D)` is the
    simultaneous double-layer turn in the G perms. Dropping the brackets would
    lose that unless the chunking reproduces it, so assert it does."""
    checked = 0
    for row in pll_rows():
        if row.source != "jperm-raw":
            continue  # owned cases follow the guide's trigger spans instead
        toks = tokenize(row.alg)
        bounds = chunk_boundaries(PLL_CHUNKS[row.name])
        for group in row.parens:
            unit = tokenize(group)
            spans = [s for s in range(len(toks) - len(unit) + 1) if toks[s : s + len(unit)] == unit]
            assert spans, f"{row.name}: {group!r} not found in its own algorithm"
            assert any(s in bounds and s + len(unit) in bounds for s in spans), (
                f"{row.name}: chunking straddles JPerm's ({group}) execution unit"
            )
            checked += 1
    assert checked == 5, f"expected 5 parenthesised units, checked {checked}"


def test_rotations_form_their_own_pll_chunk() -> None:
    """A gap on the card means "change your grip"; a rotation is the largest
    grip change there is, so it never shares a chunk with a face turn."""
    for name, chunks in PLL_CHUNKS.items():
        for chunk in chunks:
            toks = [t for seg in chunk for t in tokenize(seg)]
            if any(t[0] in "xyz" for t in toks):
                assert toks == [toks[0]] and toks[0][0] in "xyz", (
                    f"{name}: rotation shares a chunk with {toks}"
                )


def test_pll_block_is_compactable() -> None:
    """No PLL algorithm carries a layer-count prefix, so Card 3's whole block
    may drop its inner spaces — which is what makes 21 algs fit."""
    assert block_compactable(list(pll_algs().values()))


def test_segments_exist_only_to_carry_colour() -> None:
    """A compacted chunk joins its segments with no gap, so a segment split
    that no trigger family colours is invisible — and therefore a mistake.
    Applies to every compacted table; the big-cube block keeps real spaces."""
    tables = {"CHUNKS": CHUNKS, "PLL_CHUNKS": PLL_CHUNKS, "DOT": {"dot": DOT_CHUNKS}}
    for table, cases in tables.items():
        for name, chunks in cases.items():
            for chunk in chunks:
                if len(chunk) > 1:
                    assert any(family(seg) for seg in chunk), (
                        f"{table}[{name}]: segments in {chunk} render no colour"
                    )
