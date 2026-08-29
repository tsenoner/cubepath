"""Minimal Rubik's cube simulator — a **3×3×3 mirror**, gated to stay one.

Scope, and why it is fixed
--------------------------
This module models a 3×3×3 cube and nothing else, and it is not going to grow.
Every layer count in it is a literal 3: `_make_face` builds nine stickers,
`_rotate_face_cw` hardcodes the 3×3 index permutation, every strip in
`_MOVE_DEFS` is three stickers long, and `sticker_at`/`diagram_to_sim` index
with `row * 3 + col` and `2 - b`.

**The cubing.js kpuzzle is this repo's source of truth for every puzzle larger
than 3×3×3.** It already ships 4×4×4 and 5×5×5 definitions, they are already
load-bearing in `app/scripts/verify-l2e.mjs` and `app/src/lib/stickering.ts`,
and the agreed seam is that JavaScript derives big-cube state and writes JSON
which Python reads and draws — the `jperm-raw.json` pattern, generalised. Do
**not** add 4×4/5×5 logic here. That would be a second copy of a cube model the
repo already owns, in the language that owns neither the definitions nor the
verifiers. If you find yourself parameterising this file by cube size, stop.

The failure this gate closes
----------------------------
`parse_algorithm` used to be `_TOKEN_RE.findall`, which silently discarded
whatever it could not match. `3Rw` became `r` (the layer count dropped), `2R2`
became `R2` (an inner slice became an outer turn), `m'` vanished entirely, and
the standard 4×4 OLL-parity algorithm parsed, raised nothing, and returned a
confident, meaningless 3×3 state. In a repo whose whole value is the
correctness of derived algorithm data, a plausible-looking wrong picture is the
worst available outcome — worse than a crash, because nothing catches it.

So the parser now consumes the **entire** string and raises rather than drop
anything. Rejected: layer-numbered moves (`2R`, `3Rw'`), SiGN wide moves
(`Rw`, `Lw2`, `Uw2'`), wing slices (`m`), triple-turn suffixes (`R3`),
postfix group repeats (`(R' F R F')2`), and any other unrecognised text.
Accepted, because they are legitimate 3×3 notation this repo's own algorithms
use: bare lowercase wide moves (`r l u d f b`), slices (`M S E`), rotations
(`x y z`), `'`/`2` suffixes, `(…)` visual groups and `(…)×N` repeats.

Bare `r` and `Rw` mean the same turn on a 3×3, so rejecting only the SiGN
spelling looks arbitrary until you measure the corpus: across the 22 canonical
algorithms in `algs.py`, the 98 extracted OLL strings, the 55 PLL strings and
the 146 F2L strings, SiGN `w` notation appears **zero** times — while every one
of the four big-cube strings the repo stores (`OLL_PARITY`, `PLL_PARITY`,
`EDGE_PARITY_5X5`, the L2E flip) is written in it. `Rw` is therefore not a 3×3
spelling this repo uses; it is the signature of a big-cube algorithm arriving
at the wrong door, and turning it away costs nothing that exists.

That check is a heuristic on notation, not a proof: a big-cube algorithm
transcribed entirely into 3×3-legal tokens (`r U2 x r U2 …`) is, token for
token, a legal 3×3 algorithm and cannot be detected from the string alone. For
that case declare the puzzle — `Cube.solved(size=4)` and
`parse_algorithm(alg, size=4)` raise `UnsupportedPuzzleError` — and get the
state from the kpuzzle instead.

State: 6 faces × 9 stickers (row-major: idx = row*3 + col).
Standard orientation: U=Yellow, D=White, F=Red, B=Orange, R=Green, L=Blue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Face colors (standard Western, yellow top, red front)
COLORS = {"U": "Y", "D": "W", "F": "R", "B": "O", "R": "G", "L": "B"}

SIZE = 3
"""The only cube size this module models. Read the module docstring before
touching this — it is a statement of scope, not a parameter."""


class UnsupportedPuzzleError(ValueError):
    """Asked to model a puzzle that is not a 3×3×3.

    Subclasses `ValueError` so existing callers that catch one still work.
    """


class UnsupportedNotationError(ValueError):
    """A move token this module cannot faithfully model.

    Raised instead of silently dropping the token, which is what produced a
    confident wrong 3×3 state from a 4×4 algorithm. Subclasses `ValueError`.
    """


_KPUZZLE_HINT = (
    "Big-cube state comes from the cubing.js kpuzzle (app/scripts/), which "
    "writes it to JSON for Python to draw; cube.py is a 3x3-only mirror and "
    "must not grow NxN logic. See the cube.py module docstring."
)


def _require_3x3(size: int) -> None:
    """Refuse any declared puzzle size this module cannot model."""
    if size != SIZE:
        raise UnsupportedPuzzleError(
            f"cube.py models {SIZE}x{SIZE}x{SIZE} only; asked for size={size}. {_KPUZZLE_HINT}"
        )


def _make_face(color: str) -> list[str]:
    return [color] * 9


def _rotate_face_cw(face: list[str]) -> list[str]:
    """Rotate a 3×3 face 90° clockwise (row-major)."""
    # 0 1 2      6 3 0
    # 3 4 5  →   7 4 1
    # 6 7 8      8 5 2
    return [face[6], face[3], face[0], face[7], face[4], face[1], face[8], face[5], face[2]]


# Strip definitions: list of (face, idx) tuples for a 3-sticker strip.
# Each move cycles 4 strips CW. Order matters: strip[0]→strip[1]→strip[2]→strip[3]→strip[0].


def _strip(face: str, indices: list[int]) -> list[tuple[str, int]]:
    return [(face, i) for i in indices]


# Move definitions: (face_to_rotate | None, [strip0, strip1, strip2, strip3])
# Strips cycle CW: values at strip[3] go to strip[0], strip[0]→strip[1], etc.
_MOVE_DEFS: dict[str, tuple[str | None, list[list[tuple[str, int]]]]] = {
    # R CW from +x: U←F, B←U, D←B, F←D
    "R": (
        "R",
        [
            _strip("U", [2, 5, 8]),
            _strip("B", [6, 3, 0]),
            _strip("D", [2, 5, 8]),
            _strip("F", [2, 5, 8]),
        ],
    ),
    # L CW from -x: U←B, F←U, D←F, B←D
    "L": (
        "L",
        [
            _strip("U", [0, 3, 6]),
            _strip("F", [0, 3, 6]),
            _strip("D", [0, 3, 6]),
            _strip("B", [8, 5, 2]),
        ],
    ),
    # U CW from +y: F←R, L←F, B←L, R←B
    "U": (
        "U",
        [
            _strip("F", [0, 1, 2]),
            _strip("L", [0, 1, 2]),
            _strip("B", [0, 1, 2]),
            _strip("R", [0, 1, 2]),
        ],
    ),
    # D CW from -y: F←L, R←F, B←R, L←B
    "D": (
        "D",
        [
            _strip("F", [6, 7, 8]),
            _strip("R", [6, 7, 8]),
            _strip("B", [6, 7, 8]),
            _strip("L", [6, 7, 8]),
        ],
    ),
    # F CW from +z: top→right→bottom→left
    # U bottom row [6,7,8] → R left col [0,3,6] → D top row [2,1,0] → L right col [8,5,2]
    "F": (
        "F",
        [
            _strip("U", [6, 7, 8]),
            _strip("R", [0, 3, 6]),
            _strip("D", [2, 1, 0]),
            _strip("L", [8, 5, 2]),
        ],
    ),
    # B CW from -z: top→left→bottom→right
    # U top row [2,1,0] → L left col [0,3,6] → D bottom row [6,7,8] → R right col [8,5,2]
    "B": (
        "B",
        [
            _strip("U", [2, 1, 0]),
            _strip("L", [0, 3, 6]),
            _strip("D", [6, 7, 8]),
            _strip("R", [8, 5, 2]),
        ],
    ),
    # M follows L direction: U←B, F←U, D←F, B←D
    "M": (
        None,
        [
            _strip("U", [1, 4, 7]),
            _strip("F", [1, 4, 7]),
            _strip("D", [1, 4, 7]),
            _strip("B", [7, 4, 1]),
        ],
    ),
    # S follows F direction: top→right→bottom→left, middle slice
    "S": (
        None,
        [
            _strip("U", [3, 4, 5]),
            _strip("R", [1, 4, 7]),
            _strip("D", [5, 4, 3]),
            _strip("L", [7, 4, 1]),
        ],
    ),
    # E follows D direction: F←L, R←F, B←R, L←B
    "E": (
        None,
        [
            _strip("F", [3, 4, 5]),
            _strip("R", [3, 4, 5]),
            _strip("B", [3, 4, 5]),
            _strip("L", [3, 4, 5]),
        ],
    ),
}


def _apply_cw(faces: dict[str, list[str]], move: str) -> None:
    """Apply one CW turn of a base move (R/L/U/D/F/B/M/S/E)."""
    face_name, strips = _MOVE_DEFS[move]
    if face_name:
        faces[face_name] = _rotate_face_cw(faces[face_name])
    # Cycle strips: save strip[3], shift strip[2]→strip[3], etc.
    saved = [faces[f][i] for f, i in strips[3]]
    for s in range(3, 0, -1):
        for j in range(3):
            src_f, src_i = strips[s - 1][j]
            dst_f, dst_i = strips[s][j]
            faces[dst_f][dst_i] = faces[src_f][src_i]
    for j in range(3):
        dst_f, dst_i = strips[0][j]
        faces[dst_f][dst_i] = saved[j]


def _apply_ccw(faces: dict[str, list[str]], move: str) -> None:
    """Apply one CCW turn = 3 CW turns."""
    for _ in range(3):
        _apply_cw(faces, move)


# Compound moves: wide turns and rotations expressed in base moves.
_COMPOUNDS: dict[str, list[str]] = {
    "r": ["R", "M'"],
    "l": ["L", "M"],
    "u": ["U", "E'"],
    "d": ["D", "E"],
    "f": ["F", "S"],
    "b": ["B", "S'"],
    "x": ["R", "M'", "L'"],
    "y": ["U", "E'", "D'"],
    "z": ["F", "S", "B'"],
}


@dataclass
class Cube:
    """Rubik's cube state — 3x3x3 only.

    `size` exists so a caller can *declare* what it thinks it is simulating.
    Declaring anything but 3 raises rather than quietly handing back a 3x3
    answer to a big-cube question; there is no size at which this class does
    something else.
    """

    faces: dict[str, list[str]] = field(default_factory=dict)
    size: int = SIZE

    def __post_init__(self) -> None:
        _require_3x3(self.size)

    @classmethod
    def solved(cls, size: int = SIZE) -> Cube:
        _require_3x3(size)
        return cls(faces={f: _make_face(c) for f, c in COLORS.items()}, size=size)

    def copy(self) -> Cube:
        return Cube(faces={f: list(s) for f, s in self.faces.items()}, size=self.size)

    def is_solved(self) -> bool:
        return all(len(set(stickers)) == 1 for stickers in self.faces.values())

    def sticker_at(self, face: str, row: int, col: int) -> str:
        """Row-major lookup. The 3 is `SIZE`, spelled literally on purpose —
        this class is a 3x3 mirror, not an NxN model."""
        return self.faces[face][row * 3 + col]

    def u_face_solved(self) -> bool:
        return all(s == COLORS["U"] for s in self.faces["U"])

    def u_cross_solved(self) -> bool:
        """U-face edges + center are yellow."""
        return all(self.faces["U"][i] == COLORS["U"] for i in (1, 3, 4, 5, 7))

    def apply_move(self, move_str: str) -> None:
        """Apply a single move token (e.g. 'R', "R'", 'R2', 'r', 'x')."""
        # Detect prime and double
        base = move_str.rstrip("'2")
        is_prime = move_str.endswith("'")
        is_double = move_str.endswith("2")

        if base in _COMPOUNDS:
            sub_moves = _COMPOUNDS[base]
            times = 2 if is_double else 1
            for _ in range(times):
                if is_prime:
                    for sm in reversed(sub_moves):
                        self.apply_move(_invert_token(sm))
                else:
                    for sm in sub_moves:
                        self.apply_move(sm)
            return

        # Base moves: R/L/U/D/F/B/M/S/E
        if base not in _MOVE_DEFS:
            raise UnsupportedNotationError(
                f"cube.py cannot model the move {move_str!r}. {_KPUZZLE_HINT}"
            )

        if is_double:
            _apply_cw(self.faces, base)
            _apply_cw(self.faces, base)
        elif is_prime:
            _apply_ccw(self.faces, base)
        else:
            _apply_cw(self.faces, base)

    def apply(self, algorithm: str) -> None:
        """Parse and apply an algorithm string, raising on anything a 3x3
        cannot express (see `parse_algorithm`)."""
        for token in parse_algorithm(algorithm, size=self.size):
            self.apply_move(token)

    def visible_sticker(self, face: str, a: int, b: int) -> str:
        """Get sticker color using diagram (a,b) coordinates.

        Coordinate mapping from _n_sticker_pts in diagrams.py:
        - U(a,b): 3D pos (a, 3, b) → sim: U[row=b, col=a] → idx = b*3 + a
        - F(a,b): 3D pos (a, b+1, 3) → sim: F[row=2-b, col=a] → idx = (2-b)*3 + a
        - R(a,b): 3D pos (3, b+1, a) → sim: R[row=2-b, col=2-a] → idx = (2-b)*3 + (2-a)
        """
        sim_face, row, col = diagram_to_sim(face, a, b)
        return self.sticker_at(sim_face, row, col)

    def set_visible_sticker(self, face: str, a: int, b: int, value: str) -> None:
        """Write a sticker using diagram (a,b) coordinates — the inverse of
        `visible_sticker`, for marking a sticker and watching where a move
        carries it. `value` need not be a colour letter."""
        sim_face, row, col = diagram_to_sim(face, a, b)
        self.faces[sim_face][row * 3 + col] = value


def _invert_token(token: str) -> str:
    """Invert a single move token: R→R', R'→R, R2→R2."""
    if token.endswith("'"):
        return token[:-1]
    if token.endswith("2"):
        return token
    return token + "'"


def invert_algorithm(alg: str, *, size: int = SIZE) -> str:
    """Invert an algorithm: reverse the token order and invert each token."""
    return " ".join(_invert_token(t) for t in reversed(parse_algorithm(alg, size=size)))


def state_before(alg: str, *, size: int = SIZE) -> Cube:
    """The state an algorithm solves: its inverse applied to a solved cube."""
    c = Cube.solved(size)
    c.apply(invert_algorithm(alg, size=size))
    return c


def diagram_to_sim(face: str, a: int, b: int) -> tuple[str, int, int]:
    """Convert diagram (face, a, b) to simulator (face, row, col)."""
    if face == "U":
        return ("U", b, a)
    elif face == "F":
        return ("F", 2 - b, a)
    elif face == "R":
        return ("R", 2 - b, 2 - a)
    raise ValueError(f"Unknown visible face: {face!r}")


# ── Tokenizer ─────────────────────────────────────────────────────────
#
# One ordered alternation, scanned across the WHOLE string. The first three
# groups exist only to be refused: they are matched deliberately so the error
# can name what it saw instead of leaving a stray character behind. Anything
# the scanner cannot place at all lands in `bad`. Nothing is ever dropped.
#
# Order is load-bearing: `layered` must precede `sign`, and `sign` must precede
# `move`, or `3Rw` degrades to `Rw` and `Rw` degrades to `R` — the exact
# silent-truncation bug this scanner exists to end.
_SUFFIX = r"(?:2'|'|2)?"

_SCAN_RE = re.compile(
    r"(?P<layered>\d+[RLUDFBrludfb]w?[2']*)"  # 2R, 2R2, 3Rw' — big-cube only
    r"|(?P<sign>[RLUDFB]w" + _SUFFIX + r")"  # Rw, Lw2, Uw2' — SiGN, see docstring
    r"|(?P<move>[RLUDFBMSExyzrludfb]" + _SUFFIX + r")"
    r"|(?P<repeat>×\d+)"
    r"|(?P<paren>[()])"
    r"|(?P<space>\s+)"
    r"|(?P<bad>[^\s()]+)"
)

# group name -> why it is refused. `bad` is the catch-all.
_REFUSALS = {
    "layered": "a layer-numbered move; cube.py has exactly three layers",
    "sign": "SiGN wide-move notation, which in this repo only ever spells a "
    "big-cube algorithm (write a 3x3 wide move as lowercase 'r')",
    "bad": "not notation cube.py models",
}


def _word_at(alg: str, index: int) -> str:
    """The whitespace-delimited word containing `index`.

    The scanner may notice the problem partway through a token (`R3` is a
    legal `R` followed by an orphan `3`), so errors quote the whole word —
    that is the string the reader has to go and find.
    """
    start, end = index, index
    while start > 0 and not alg[start - 1].isspace():
        start -= 1
    while end < len(alg) and not alg[end].isspace():
        end += 1
    return alg[start:end]


def _scan(alg: str, size: int) -> list[str]:
    """Whole-string tokenizer. Raises on anything a 3x3 cannot express."""
    _require_3x3(size)
    tokens: list[str] = []
    pos = 0
    for m in _SCAN_RE.finditer(alg):
        if m.start() != pos:  # unreachable while `bad` matches everything
            raise UnsupportedNotationError(f"unparsed text {alg[pos : m.start()]!r} in {alg!r}")
        pos = m.end()
        kind = m.lastgroup
        assert kind is not None
        if kind in _REFUSALS:
            word = _word_at(alg, m.start())
            raise UnsupportedNotationError(
                f"refusing to simulate {word!r} in {alg!r}: {_REFUSALS[kind]}. {_KPUZZLE_HINT}"
            )
        if kind == "space":
            continue
        tok = m.group()
        # `X2'` and `X2` are the same half turn; normalise so `apply_move`'s
        # prime/double detection cannot read the apostrophe as a direction.
        tokens.append(tok[:-1] if tok.endswith("2'") else tok)
    if pos != len(alg):
        raise UnsupportedNotationError(f"unparsed trailing text {alg[pos:]!r} in {alg!r}")
    return tokens


def parse_algorithm(alg: str, *, size: int = SIZE) -> list[str]:
    """Parse an algorithm string into move tokens, or raise.

    Supports: R U R' U' R2, lowercase wide (r, f), rotations, slices, and
    parenthesized repeats (R U)×2. Parentheses not followed by a repeat count
    are visual grouping only: a closed group is held until the next token — a
    ×N multiplies it, anything else (a move, another "(", or the end of the
    string) flushes it in order.

    Raises `UnsupportedNotationError` on any token a 3x3 cannot express, and
    `UnsupportedPuzzleError` if `size` is not 3. It never silently drops a
    token — see the module docstring for what that used to cost.
    """
    tokens = _scan(alg, size)
    result: list[str] = []
    group: list[str] | None = None  # open "(… " being collected
    closed: list[str] | None = None  # "(…)" seen, awaiting a possible ×N

    def flush_closed() -> None:
        nonlocal closed
        if closed is not None:
            result.extend(closed)
            closed = None

    for tok in tokens:
        if tok == "(":
            flush_closed()
            if group is not None:  # unbalanced "(" — keep the open group's moves
                result.extend(group)
            group = []
        elif tok == ")":
            if group is None:
                flush_closed()  # stray ")" — nothing to close
            else:
                closed, group = group, None
        elif tok.startswith("×"):
            if closed is None:
                raise UnsupportedNotationError(
                    f"repeat count {tok!r} in {alg!r} follows no '(...)' group"
                )
            result.extend(closed * int(tok[1:]))
            closed = None
        elif group is not None:
            group.append(tok)
        else:
            flush_closed()
            result.append(tok)

    flush_closed()
    if group is not None:  # unclosed "(" — keep its moves
        result.extend(group)

    return result
