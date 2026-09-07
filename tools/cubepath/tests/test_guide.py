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

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STAMP_SCRIPT = ROOT / "scripts" / "guide_stamp.py"


def _guide_inputs() -> list[Path]:
    """Every file the PDF is built from, from the stamp's own reader.

    `inputs()` raises on a dangling `](figures/...svg)` link, so a diagram
    renamed out from under the guide fails here rather than in pandoc.
    """
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:  # two callers now; do not grow sys.path per test
        sys.path.insert(0, scripts)
    # Loaded off sys.path at call time: repo `scripts/` is not an importable
    # package, so mypy cannot resolve it statically.
    import guide_stamp  # type: ignore[import-not-found]

    return list(guide_stamp.inputs())


def test_the_shipped_pdf_is_current_with_the_guide_source() -> None:
    result = subprocess.run(
        [sys.executable, str(STAMP_SCRIPT), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_figure_the_guide_references_exists() -> None:
    files = _guide_inputs()
    figures = [f for f in files if f.suffix == ".svg"]
    assert len(figures) == 52, f"guide references {len(figures)} figures, expected 52"
    assert all(f.is_file() for f in files)


def test_claude_md_states_the_same_figure_count() -> None:
    """CLAUDE.md says the number twice, in prose, and both copies were hand-
    edited 51 -> 52 with nothing to catch a missed one. Parse rather than
    restate — `test_conventions.py` does the same to that document's cube
    conventions, and for the same reason: prose does not run."""
    expected = len([f for f in _guide_inputs() if f.suffix == ".svg"])
    text = (ROOT / "CLAUDE.md").read_text()
    for pattern in (r"only the (\d+) figures", r"references (\d+) of them"):
        claimed = [int(m) for m in re.findall(pattern, text)]
        assert claimed, f"CLAUDE.md: nothing matched {pattern!r} — the gate stopped reading"
        for n in claimed:
            assert n == expected, f"CLAUDE.md says {n} figures, the guide references {expected}"


def test_no_figure_asks_for_a_rotation_the_filter_no_longer_performs() -> None:
    """`rotate=` is dead markup now, and dead markup that renders is the trap.

    The Lua `Image` handler that implemented `![alt](x.svg){ rotate=180 }` was
    deleted once the Hook was drawn at both holds: a second way to orient a
    picture is how a back-left picture shipped beside a front-right cue. Pandoc
    passes an unknown image attribute straight through to the typst writer,
    which ignores it — so a `rotate=` added later would build clean, ship
    unrotated, and be caught by nothing. Fail loudly instead, and say what to do.
    """
    lua = (ROOT / "guide" / "filters" / "callouts.lua").read_text()
    assert "function Image(" not in lua, (
        "callouts.lua defines an Image filter again — if rotation is back, "
        "delete this test; if it is not, delete the filter"
    )
    source = (ROOT / "guide" / "cubepath.md").read_text()
    assert "rotate=" not in source, (
        "guide/cubepath.md uses `rotate=`, which nothing implements any more — "
        "draw the figure at the hold it teaches (see `_oll_cross_cases`)"
    )
