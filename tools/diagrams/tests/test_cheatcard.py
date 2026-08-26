"""End-to-end gates on the generated cheat card PDF.

Typst and poppler are not installed in CI (which runs `make check-py` with uv
only), so these skip there. The generator itself runs the same gates on every
build, so a broken card cannot be produced locally either way.
"""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from cubepath import cheatcards
from cubepath.diagrams import CARD_FACES, SCREEN_FACES
from cubepath.notation import CHUNKS, compact

pytestmark = pytest.mark.skipif(
    not all(shutil.which(t) for t in ("typst", "pdfinfo", "pdftotext", "pdffonts")),
    reason="needs typst + poppler",
)


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    """Build the card once into a temp dir, leaving guide/build alone."""
    out = tmp_path_factory.mktemp("card")
    cheatcards.build_print_svgs()
    cheatcards.write_sources()
    pdf = out / "cheat-card.pdf"
    cheatcards._compile(cheatcards._OUT / "cheat-card.typ", pdf)
    return pdf


def test_card_is_exactly_two_id1_pages(card) -> None:
    """Typst paginates silently on overflow — a third page means the content
    no longer fits the card."""
    info = cheatcards._pdfinfo(card)
    assert info["Pages"] == "2"
    w, h = (float(v) for v in re.match(r"([\d.]+) x ([\d.]+)", info["Page size"]).groups())
    assert abs(w - cheatcards.CARD_W * 72 / 25.4) < 0.1
    assert abs(h - cheatcards.CARD_H * 72 / 25.4) < 0.1


def test_no_smart_quotes(card) -> None:
    """Typst rewrites ASCII primes to U+2019, which cubing.js refuses to
    parse — an algorithm copied off the card would not run."""
    text = subprocess.run(["pdftotext", str(card), "-"], capture_output=True, text=True).stdout
    assert "’" not in text
    assert "′" not in text
    assert "R'" in text


def test_every_algorithm_appears_in_the_pdf(card) -> None:
    text = subprocess.run(["pdftotext", str(card), "-"], capture_output=True, text=True).stdout
    flat = re.sub(r"\s+", "", text)
    for key, chunks in CHUNKS.items():
        for chunk in chunks:
            for seg in chunk:
                assert compact(seg) in flat, f"{key}: segment {seg!r} missing from the card"


def test_only_bundled_fonts(card) -> None:
    """Typst exits 0 on an unknown family, so a macOS-only font would render
    here and fall back to something else on every other machine."""
    fonts = subprocess.run(["pdffonts", str(card)], capture_output=True, text=True).stdout
    assert "DejaVuSansMono" in fonts
    for banned in ("Courier", "Helvetica", "Arial", "Times"):
        assert banned not in fonts, f"non-bundled font {banned} reached the PDF"


def test_card_diagrams_are_rendered_in_card_style(tmp_path) -> None:
    """The card's diagrams must come off the generator in CARD style, not off
    the screen SVGs. A screen colour reaching the card means the re-render
    silently stopped happening."""
    counts = cheatcards.build_print_svgs()
    assert counts == {"oll": 11, "pll": 6}, counts
    seen = set()
    for svg in sorted((cheatcards._CARD_SVG).rglob("*.svg")):
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
