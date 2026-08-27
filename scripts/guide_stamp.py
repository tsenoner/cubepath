#!/usr/bin/env python3
"""Freshness stamp for the committed guide PDF.

`app/public/cubepath.pdf` is a build output that ships to production, but CI
never runs `make build-guide` (no pandoc, typst or poppler on the runner), so
nothing would notice it going stale — and it did, by two content revisions.
The same reasoning already produced `tests/test_cards.py` for `cards.json` and
`test_logo.py` for `favicon.svg`; this is that gate for the PDF.

A PDF cannot be compared to its source, and typst output is not byte-
reproducible, so we stamp the *inputs* instead: `make build-guide` writes the
digest of everything the PDF is built from, and `--check` recomputes it. Edit
the guide and forget to rebuild, and the digests disagree.

    python3 scripts/guide_stamp.py --write   # after building the PDF
    python3 scripts/guide_stamp.py --check   # gate (tests/test_guide.py)

Inputs are the markdown, the pandoc/typst configuration, the Lua filter, and
only the figures `cubepath.md` actually references — the 78 `oll-full/` and
`pll-full/` SVGs are app assets the guide never draws, so churning them must
not force a PDF rebuild.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "guide"
SOURCE = GUIDE / "cubepath.md"
PDF = ROOT / "app" / "public" / "cubepath.pdf"
STAMP = GUIDE / "pdf.stamp.json"

# Everything pandoc reads that is not a figure. Globs, so a file added to
# styles/ or templates/ is covered without editing this list.
CONFIG_GLOBS = ("metadata.yaml", "defaults/*", "filters/*", "styles/*", "templates/*")

_LINK = re.compile(r"]\(([^)]+\.svg)\)")


def inputs() -> list[Path]:
    """Every file the PDF is built from, repo-relative and sorted."""
    found = [SOURCE]
    for pattern in CONFIG_GLOBS:
        found += sorted(GUIDE.glob(pattern))
    figures = {GUIDE / ref for ref in _LINK.findall(SOURCE.read_text())}
    missing = sorted(str(f.relative_to(ROOT)) for f in figures if not f.is_file())
    if missing:
        raise SystemExit(f"guide references figures that do not exist: {missing}")
    return sorted(set(found) | figures)


def digest() -> tuple[str, int]:
    h = hashlib.sha256()
    files = inputs()
    for path in files:
        h.update(str(path.relative_to(ROOT)).encode())
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest(), len(files)


def write() -> None:
    sha, count = digest()
    STAMP.write_text(
        json.dumps(
            {
                "_": "Written by `make build-guide`. Checked by tests/test_guide.py.",
                "inputs_sha256": sha,
                "input_files": count,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"guide stamp: {sha[:12]}… over {count} input files")


def check() -> None:
    if not PDF.is_file():
        raise SystemExit(f"{PDF.relative_to(ROOT)} is missing — run `make build-guide`")
    if not STAMP.is_file():
        raise SystemExit(f"{STAMP.relative_to(ROOT)} is missing — run `make build-guide`")
    sha, count = digest()
    stored = json.loads(STAMP.read_text())
    if stored.get("inputs_sha256") != sha:
        raise SystemExit(
            "app/public/cubepath.pdf is stale: the guide inputs changed since it was\n"
            f"built ({count} files now hash to {sha[:12]}…, stamp says "
            f"{str(stored.get('inputs_sha256'))[:12]}…).\n"
            "Run `make build-guide` and commit the PDF plus guide/pdf.stamp.json."
        )
    print(f"guide stamp ok: {sha[:12]}… over {count} input files")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "--write":
        write()
    elif mode == "--check":
        check()
    else:
        raise SystemExit(__doc__)
