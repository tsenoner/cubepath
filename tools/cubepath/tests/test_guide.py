"""Gate on the guide PDF that ships from `app/public/`.

Same contract as `test_cards.py` for `cards.json` and `test_logo.py` for
`favicon.svg`: CI never runs `make build-guide` — no pandoc, typst or poppler
on the runner — so without a gate here nothing catches the committed PDF going
stale, which is exactly how it fell two content revisions behind.

The PDF itself is not comparable to its source (typst output is not byte-
reproducible), so `scripts/guide_stamp.py` stamps the *inputs*: the digest is
written by `make build-guide` and recomputed here. It is pure Python and
dependency-free, so unlike the PDF assertions in `test_cards.py` this one does
not skip in CI.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STAMP_SCRIPT = ROOT / "scripts" / "guide_stamp.py"


def test_the_shipped_pdf_is_current_with_the_guide_source() -> None:
    result = subprocess.run(
        [sys.executable, str(STAMP_SCRIPT), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_figure_the_guide_references_exists() -> None:
    """`inputs()` raises on a dangling `](figures/...svg)` link, so a diagram
    renamed out from under the guide fails here rather than in pandoc."""
    sys.path.insert(0, str(ROOT / "scripts"))
    # Loaded off sys.path at call time: repo `scripts/` is not an importable
    # package, so mypy cannot resolve it statically.
    import guide_stamp  # type: ignore[import-not-found]

    files = guide_stamp.inputs()
    figures = [f for f in files if f.suffix == ".svg"]
    assert len(figures) == 52, f"guide references {len(figures)} figures, expected 52"
    assert all(f.is_file() for f in files)
