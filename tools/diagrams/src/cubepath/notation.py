"""Card notation: chunking, compaction, and the big-cube algorithm sources.

The card renders algorithms in a compacted form — spaces removed *inside* a
chunk, a wide gap *between* chunks — so a 17-move alg reads as four grabbable
execution units instead of seventeen loose tokens.

Two invariants make that safe:

1.  **Lossless.** A chunk list is data *over* the canonical string, never a
    retyped algorithm. `expand(CHUNKS[key]) == ALGORITHMS[key]` character for
    character, asserted for every key in `tests/test_notation.py`.
2.  **Unambiguous.** Space removal is refused for any algorithm carrying a
    layer-count prefix (`2R`, `3Rw`). `2R2 U2` compacted to `2R2U2` has two
    legal readings and the wrong one is a different cube state, so the whole
    big-cube block keeps its spaces and only the inter-chunk gap survives.

A chunk is a list of *segments*. Segments exist so a conjugate wrapper can be
coloured on the inside — `F` `R U R' U'` `F'` prints as one visual unit with
the sexy move picked out — while still expanding to a flat token stream.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from cubepath.palette import FAMILY

_REPO = Path(__file__).resolve().parents[4]

# One cube move: optional layer-count prefix, a face/slice/rotation letter, an
# optional 'w' width flag, and an optional modifier.
TOKEN = re.compile(r"\d*[RULDFBMESrlufbdxyz]w?(?:'2|2'|'|2)?")


def tokenize(alg: str) -> list[str]:
    """Split an algorithm into moves, raising if anything is unrecognised."""
    tokens, pos = [], 0
    for m in TOKEN.finditer(alg):
        if alg[pos : m.start()].strip():
            raise ValueError(f"unparsed text {alg[pos : m.start()]!r} in {alg!r}")
        tokens.append(m.group())
        pos = m.end()
    if alg[pos:].strip():
        raise ValueError(f"unparsed trailing text {alg[pos:]!r} in {alg!r}")
    return tokens


def compactable(alg: str) -> bool:
    """False if any token carries a layer-count prefix (2R, 3Rw, ...).

    Those cannot have their spaces removed: `2R2 U2` -> `2R2U2` also reads as
    `2R 2U2`, and the two are different cube states.
    """
    return not any(t[0].isdigit() for t in tokenize(alg))


def compact(alg: str) -> str:
    """Drop the spaces inside one segment. Raises if that would be ambiguous."""
    if not compactable(alg):
        raise ValueError(f"refusing to compact layer-prefixed algorithm {alg!r}")
    return "".join(tokenize(alg))


Chunk = list[str]  # segments, each a space-separated token string


def expand(chunks: list[Chunk]) -> str:
    """Flatten a chunk list back to its canonical space-separated form."""
    return " ".join(t for chunk in chunks for seg in chunk for t in tokenize(seg))


def family(segment: str) -> str | None:
    """The trigger family of a segment, or None. Never hand-assigned."""
    return FAMILY.get(" ".join(tokenize(segment)))


# ── Chunk tables ──────────────────────────────────────────────────────
# Boundaries follow the guide's own trigger spans, so the card and the guide
# build one memory rather than two.

CHUNKS: dict[str, list[Chunk]] = {
    "Sexy Move": [["R U R' U'"]],
    "Lefty": [["L' U' L U"]],
    "F-sexy-F'": [["F", "R U R' U'", "F'"]],
    "f-sexy-f'": [["f", "R U R' U'", "f'"]],
    "Sune": [["R U R' U"], ["R U2 R'"]],
    "Niklas": [["R U' L' U"], ["R' U' L"]],
    "Anti-Sune": [["R U2 R'"], ["U' R U' R'"]],
    "Pi": [["f", "R U R' U'", "f'"], ["F", "R U R' U'", "F'"]],
    "Headlights": [["R2 D R' U2"], ["R D' R' U2 R'"]],
    "Double Headlights": [["R U R' U"], ["R U' R'"], ["U R U2 R'"]],
    "Chameleon": [["r U R' U'", "r'"], ["F R F'"]],
    "Bowtie": [["F'", "r U R' U'", "r'"], ["F R"]],
    "T-Perm": [["R U R' U'"], ["R' F"], ["R2 U' R' U'"], ["R U R' F'"]],
    "Y-Perm": [["F R U' R' U'"], ["R U R' F'"], ["R U R' U'"], ["R' F R F'"]],
    "Ua": [["M2 U"], ["M U2"], ["M' U M2"]],
    "Ub": [["R2 U"], ["R U R' U'"], ["R' U'"], ["R' U R'"]],
    "H-Perm": [["M2 U' M2"], ["U2"], ["M2 U' M2"]],
    "Z-Perm": [["M' U'"], ["M2 U' M2 U'"], ["M' U2"], ["M2 U"]],
    # Phase 1 finishers
    "Edge Insert Right": [["U"], ["R U R' U'"], ["y"], ["L' U' L U"]],
    "Edge Insert Left": [["U'"], ["L' U' L U"], ["y'"], ["R U R' U'"]],
    "Orient Corners Right": [["R' D' R D"]],
    "Orient Corners Front": [["D' R' D R"]],
}

# These print as one chunk plus a literal "x2" label; the stored algorithm is
# the doubled token stream (cubing notation has no repeat operator, and `x2`
# would collide with the x rotation the 4x4 parity alg actually contains).
REPEATED: frozenset[str] = frozenset({"Orient Corners Right", "Orient Corners Front"})

DOT_CHUNKS: list[Chunk] = [["F", "R U R' U'", "F'"], ["f", "R U R' U'", "f'"]]


def expand_key(key: str) -> str:
    """Expand a key's printed chunks back to its canonical algorithm.

    A repeated algorithm prints once with an "x2" label, so its printed form
    expands to half the stored string — double it before comparing.
    """
    flat = expand(CHUNKS[key])
    return f"{flat} {flat}" if key in REPEATED else flat


def block_compactable(algs: list[str]) -> bool:
    """Whether a whole block may drop its inner spaces.

    Applied per block, not per algorithm: mixing compacted and spaced rows in
    one visual group would make the gap stop meaning "new grip". One
    layer-prefixed algorithm anywhere in the block spaces the entire block.
    """
    return all(compactable(a) for a in algs)


# ── Big-cube algorithms, sourced from the files that already verify them ──
# Nothing here is retyped. Each string is read back out of the module that
# pins it for CI, so the card cannot drift from the verifier.

_EXTRACT = _REPO / "app" / "scripts" / "extract-algs.mjs"
_VERIFY_L2E = _REPO / "app" / "scripts" / "verify-l2e.mjs"
_L2E_DATA = _REPO / "app" / "src" / "data" / "extracted" / "l2e-raw.json"


def _js_const(path: Path, name: str) -> str:
    """Read a `const NAME = "...";` string out of a JS source file."""
    m = re.search(rf'^const {name} = "([^"]+)";', path.read_text(), re.M)
    if not m:
        raise AssertionError(f"{name} not found in {path} — the card's source moved")
    return m.group(1)


def bigcube_algs() -> dict[str, str]:
    """The four big-cube strings the card prints, from their verified sources."""
    l2e = json.loads(_L2E_DATA.read_text())
    flip = next(c for c in l2e if c["slug"] == "l2e-1")["algs"][0]
    return {
        # verified on the 5x5 kpuzzle by verify-l2e.mjs; also legal on the 4x4
        "l2e-flip": flip,
        # pinned in extract-algs.mjs and cross-checked against jperm's lib files
        "4x4-oll-parity": _js_const(_EXTRACT, "OLL_PARITY"),
        "4x4-pll-parity": _js_const(_EXTRACT, "PLL_PARITY"),
        # pinned in verify-l2e.mjs; differs from the 4x4 form by one token
        "5x5-edge-parity": _js_const(_VERIFY_L2E, "EDGE_PARITY_5X5"),
    }


# Chunkings for the big-cube algs. These blocks are NOT compacted (see
# `compactable`): every one of them carries a layer-count prefix somewhere in
# the block, so spaces stay and only the inter-chunk gap encodes structure.
BIGCUBE_CHUNKS: dict[str, list[Chunk]] = {
    "l2e-flip": [["Rw'"], ["U' R' U"], ["R' F R F'"], ["Rw"]],
    "4x4-pll-parity": [["2R2 U2"], ["2R2 Uw2"], ["2R2 Uw2"]],
    "4x4-oll-parity": [["Rw U2 x Rw U2 Rw U2 Rw' U2"], ["Lw U2 Rw' U2"], ["Rw U2 Rw' U2 Rw'"]],
    "5x5-edge-parity": [["Rw U2 x Rw U2 Rw U2 3Rw' U2"], ["Lw U2 Rw' U2"], ["Rw U2 Rw' U2 Rw'"]],
}

# The one token that separates the 4x4 and 5x5 parity algorithms. Printed as a
# fixed-width cell on the 4x4 line so the two lines align token-for-token, and
# highlighted on the 5x5 line. verify-l2e.mjs pins the same index.
PARITY_DIFF_INDEX = 7
PARITY_DIFF_4X4 = "Rw'"
PARITY_DIFF_5X5 = "3Rw'"
