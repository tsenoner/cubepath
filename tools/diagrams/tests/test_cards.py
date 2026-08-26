"""End-to-end gates on the generated card set.

Typst and poppler are not installed in CI (which runs `make check-py` with uv
only), so the PDF tests skip there. The generator runs the same gates on every
build, so a broken card cannot be produced locally either way. The pure-Python
tests — imposition, deck, vocabulary — run everywhere.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from cubepath import cheatcards
from cubepath.cards import DECK, FRONT_SLOTS, Row, learn_order, pll_deck
from cubepath.cheatcards import RHO, SHEETS, SIGMA_LONG, SIGMA_SHORT
from cubepath.diagrams import CARD_FACES, SCREEN_FACES
from cubepath.glossary import BANNED, DEMONSTRATED, GLOSS, TEACH
from cubepath.notation import CHUNKS, PLL_CHUNKS, compact

_TOOLS = ("typst", "pdfinfo", "pdftotext", "pdffonts")
needs_typst = pytest.mark.skipif(
    not all(shutil.which(t) for t in _TOOLS), reason="needs typst + poppler"
)


# ── Deck (pure Python, runs in CI) ────────────────────────────────────


def test_deck_is_three_cards_and_an_annex() -> None:
    assert [c.num for c in DECK] == [1, 2, 3, None]
    assert [c.index for c in DECK] == [0, 1, 2, 3]
    assert len({c.slug for c in DECK}) == 4


def test_supersession_is_symmetric() -> None:
    """Exactly one seam, and it must be printed on both sides of it."""
    by_slug = {c.slug: c for c in DECK}
    pairs = [(c.slug, c.superseded_by) for c in DECK if c.superseded_by]
    assert pairs == [("first-solve", "two-look")], pairs
    for slug, nxt in pairs:
        assert by_slug[nxt].supersedes == slug
        assert any("retired" in n for n in by_slug[slug].notes)
        assert any("retired" in n for n in by_slug[nxt].notes)


def test_every_gate_is_a_count_not_a_clock() -> None:
    """A clock at these tiers measures the method, not the solver. Times are
    MASTER checkboxes with a write-in target, never an unlock."""
    for card in DECK:
        assert not re.search(r"\d+:\d\d|\bunder \d", card.unlock), card.unlock
        if card.master:
            assert "My target: ______" in card.master, card.master


def test_progress_boxes_start_filled() -> None:
    """Card 1 arrives with one box already filled — true of anyone holding it,
    and the cheapest completion nudge there is."""
    assert [c.filled for c in DECK] == [1, 2, 3, 0]


def test_learn_order_covers_every_unowned_case() -> None:
    assert len(learn_order()) == 15
    assert len(pll_deck()) == 21
    assert all(isinstance(r, Row) for r in pll_deck().values())


# ── Imposition (pure Python, runs in CI) ──────────────────────────────


def test_front_list_is_row_duplicated() -> None:
    """The theorem the duplex scheme rests on. A reorder that interleaves
    cards scrambles every duplex print with no symptom on a proof sheet."""
    cheatcards.check_row_duplication()
    assert FRONT_SLOTS == [0, 0, 1, 1, 2, 2, 3, 3]


def test_permutations_are_involutions() -> None:
    for sigma in (SIGMA_LONG, SIGMA_SHORT, RHO):
        assert [sigma[sigma[s]] for s in range(8)] == list(range(8)), sigma
    assert SIGMA_SHORT == [RHO[SIGMA_LONG[s]] for s in range(8)]


@pytest.mark.parametrize("sheet", sorted(SHEETS))
def test_mirror_invariance(sheet: str) -> None:
    """Never `==`: 40.54 + 202.48 + 53.98 sums to 297.00000000000006."""
    cheatcards.check_mirror(*SHEETS[sheet])


def test_naive_rotation_alone_would_pair_the_wrong_faces() -> None:
    """The trap this scheme exists to avoid, asserted so it stays avoided: a
    whole-page 180 rotation on its own degenerates into the long-edge column
    swap, which pairs Card 1's front with Card 2's back once the cards differ.
    """
    interleaved = [0, 1, 2, 3, 0, 1, 2, 3]
    assert [interleaved[RHO[s]] for s in range(8)] != interleaved


@pytest.mark.parametrize("flip", ["long", "short"])
def test_only_the_short_edge_file_rotates_page_two(flip: str) -> None:
    src = cheatcards._duplex(210.0, 297.0, flip)
    assert (f"flip on the {flip.upper()} edge").lower() in src.lower()
    assert ("rotate(180deg, origin: center + horizon" in src) == (flip == "short")


# ── Vocabulary (pure Python, runs in CI) ──────────────────────────────


def test_banned_terms_have_replacements() -> None:
    assert all(v for v in BANNED.values())
    assert set(BANNED) & set(GLOSS) == set(), "a term cannot be both taught and banned"


def test_every_tier_is_defined() -> None:
    """A term in TEACH with no gloss would silently never be enforced."""
    assert TEACH <= set(GLOSS), sorted(TEACH - set(GLOSS))
    assert DEMONSTRATED <= set(GLOSS), sorted(DEMONSTRATED - set(GLOSS))
    assert not (TEACH & DEMONSTRATED), "a term is either said or shown, not both"


def test_glosses_are_short() -> None:
    for term, gloss in GLOSS.items():
        assert len(gloss.split()) <= 12, f"{term}: gloss is a paragraph, not a gloss"


# ── The rendered PDFs ─────────────────────────────────────────────────


@pytest.fixture(scope="module")
def built():
    """Build the whole set once; return each card's extracted text."""
    cheatcards.build_print_svgs()
    cheatcards.write_sources()
    out = {}
    for card in DECK:
        pdf = cheatcards._OUT / f"card-{card.index}-{card.slug}.pdf"
        cheatcards._compile(cheatcards._OUT / f"card-{card.index}-{card.slug}.typ", pdf)
        out[card.slug] = (pdf, cheatcards.pdf_text(pdf))
    return out


@needs_typst
@pytest.mark.parametrize("card", DECK, ids=lambda c: c.slug)
def test_each_card_is_two_id1_pages(built, card) -> None:
    """Typst paginates silently on overflow — a third page means the content
    no longer fits."""
    info = cheatcards._pdfinfo(built[card.slug][0])
    assert info["Pages"] == "2"
    w, h = (float(v) for v in re.match(r"([\d.]+) x ([\d.]+)", info["Page size"]).groups())
    assert abs(w - cheatcards.CARD_W * 72 / 25.4) < 0.1
    assert abs(h - cheatcards.CARD_H * 72 / 25.4) < 0.1


@needs_typst
def test_no_card_overflows_its_own_height(built) -> None:
    """The gate that replaces hand arithmetic. A fixed-height card does not
    paginate when it overruns — it overlaps its own footer, which the page
    count cannot see. This is measured in Typst on the real rendering."""
    heights = cheatcards.measure_faces()
    assert len(heights) == 8
    for face, mm in heights.items():
        assert mm <= cheatcards.USABLE_H, f"{face} needs {mm}mm of {cheatcards.USABLE_H}mm"


@needs_typst
@pytest.mark.parametrize("card", DECK, ids=lambda c: c.slug)
def test_no_smart_quotes(built, card) -> None:
    """Typst rewrites ASCII primes to U+2019, which cubing.js refuses to
    parse — an algorithm copied off the card would not run."""
    text = built[card.slug][1]
    assert "’" not in text and "′" not in text


@needs_typst
def test_every_algorithm_appears_in_the_set(built) -> None:
    flat = re.sub(r"\s+", "", "".join(t for _, t in built.values()))
    for key, chunks in {**CHUNKS, **PLL_CHUNKS}.items():
        for chunk in chunks:
            for seg in chunk:
                assert compact(seg) in flat, f"{key}: segment {seg!r} missing from the set"


@needs_typst
@pytest.mark.parametrize("card", DECK, ids=lambda c: c.slug)
def test_no_banned_term_reaches_a_card(built, card) -> None:
    text = built[card.slug][1]
    for term, better in BANNED.items():
        assert not re.search(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", text, re.IGNORECASE), (
            f"{card.slug}: {term!r} should be {better!r}"
        )


@needs_typst
@pytest.mark.parametrize("card", DECK, ids=lambda c: c.slug)
def test_taught_terms_are_glossed_on_their_own_card(built, card) -> None:
    """Definition-on-*this*-card, not defined-earlier-in-the-set. A term
    defined on Card 1 is forgotten by Card 3, and the annex is cuttable."""

    # pdftotext is lossy at a line wrap: a hyphenated compound comes back with
    # the hyphen gone and sometimes with no space either ("look-ahead" ->
    # "lookahead"). Compare on letters alone so the gate tests the card, not
    # the extractor.
    def squash(x: str) -> str:
        return re.sub(r"[^a-z0-9=]+", "", x.lower())

    text = squash(built[card.slug][1])
    for term in TEACH:
        if squash(term) not in text:
            continue
        assert squash(f"{term}={GLOSS[term]}") in text, (
            f"{card.slug} uses {term!r} without printing its gloss on this card"
        )


@needs_typst
@pytest.mark.parametrize("card", DECK, ids=lambda c: c.slug)
def test_calibration_tick_on_every_back(built, card) -> None:
    """Sheet furniture does not survive the scissors."""
    assert "20 mm" in built[card.slug][1]


@needs_typst
@pytest.mark.parametrize("card", DECK, ids=lambda c: c.slug)
def test_no_raw_typst_markup_reaches_the_page(built, card) -> None:
    flat = re.sub(r"\s+", "", built[card.slug][1])
    for leak in cheatcards._LEAKS:
        assert leak.replace(" ", "") not in flat, f"{card.slug}: {leak!r} rendered as text"


@needs_typst
@pytest.mark.parametrize("card", DECK, ids=lambda c: c.slug)
def test_only_bundled_fonts(built, card) -> None:
    """Typst exits 0 on an unknown family, so a macOS-only font would render
    here and fall back to something else on every other machine."""
    fonts = subprocess.run(
        ["pdffonts", str(built[card.slug][0])], capture_output=True, text=True
    ).stdout
    assert "DejaVuSansMono" in fonts
    for banned in ("Courier", "Helvetica", "Arial", "Times"):
        assert banned not in fonts, f"non-bundled font {banned} reached the PDF"


def test_card_diagrams_are_rendered_in_card_style() -> None:
    """The cards' diagrams must come off the generator in CARD style, not off
    the screen SVGs. A screen colour reaching a card means the re-render
    silently stopped happening."""
    counts = cheatcards.build_print_svgs()
    assert counts == {"oll": 11, "pll": 6, "pll-full": 21, "steps": 19}, counts
    seen = set()
    for svg in sorted(cheatcards._CARD_SVG.rglob("*.svg")):
        text = svg.read_text()
        for letter, hex_ in SCREEN_FACES.items():
            if hex_ == CARD_FACES[letter]:
                continue  # deliberately identical in both styles (Y, W)
            assert f'fill="{hex_}"' not in text, f"{svg.name}: screen {letter} survived"
        for hex_ in CARD_FACES.values():
            if f'fill="{hex_}"' in text:
                seen.add(hex_)
        assert 'fill="#C0C0C0"' not in text, f"{svg.name}: screen masked grey survived"
    assert seen, "no card face colour reached any diagram"


def test_manifest_matches_the_deck() -> None:
    rows = cheatcards.manifest()
    assert [r["route"] for r in rows] == ["/c0", "/c1", "/c2", "/c3"]
    assert [r["slug"] for r in rows] == [c.slug for c in DECK]
    for r in rows:
        assert set(r["fold_pdf"]) == set(SHEETS)
    json.dumps(rows)  # must be serialisable — the app reads it
