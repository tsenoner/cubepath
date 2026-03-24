"""Minimal Rubik's cube simulator for verifying diagrams and algorithms.

State: 6 faces × 9 stickers (row-major: idx = row*3 + col).
Standard orientation: U=Yellow, D=White, F=Red, B=Orange, R=Green, L=Blue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Face colors (standard Western, yellow top, red front)
COLORS = {"U": "Y", "D": "W", "F": "R", "B": "O", "R": "G", "L": "B"}


def _make_face(color: str) -> list[str]:
    return [color] * 9


def _rotate_face_cw(face: list[str]) -> list[str]:
    """Rotate a 3×3 face 90° clockwise (row-major)."""
    # 0 1 2      6 3 0
    # 3 4 5  →   7 4 1
    # 6 7 8      8 5 2
    return [face[6], face[3], face[0], face[7], face[4], face[1], face[8], face[5], face[2]]


def _rotate_face_ccw(face: list[str]) -> list[str]:
    return [face[2], face[5], face[8], face[1], face[4], face[7], face[0], face[3], face[6]]


def _rotate_face_180(face: list[str]) -> list[str]:
    return [face[8], face[7], face[6], face[5], face[4], face[3], face[2], face[1], face[0]]


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


@dataclass
class Cube:
    """Rubik's cube state."""

    faces: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def solved(cls) -> Cube:
        return cls(faces={f: _make_face(c) for f, c in COLORS.items()})

    def copy(self) -> Cube:
        return Cube(faces={f: list(s) for f, s in self.faces.items()})

    def is_solved(self) -> bool:
        return all(len(set(stickers)) == 1 for stickers in self.faces.values())

    def sticker_at(self, face: str, row: int, col: int) -> str:
        return self.faces[face][row * 3 + col]

    def u_face_solved(self) -> bool:
        return all(s == COLORS["U"] for s in self.faces["U"])

    def u_corners_oriented(self) -> bool:
        """All 4 U-face corners are yellow."""
        return all(self.faces["U"][i] == COLORS["U"] for i in (0, 2, 6, 8))

    def u_cross_solved(self) -> bool:
        """U-face edges + center are yellow."""
        return all(self.faces["U"][i] == COLORS["U"] for i in (1, 3, 4, 5, 7))

    def apply_move(self, move_str: str) -> None:
        """Apply a single move token (e.g. 'R', "R'", 'R2', 'r', 'x')."""
        # Detect prime and double
        base = move_str.rstrip("'2")
        is_prime = move_str.endswith("'")
        is_double = move_str.endswith("2")

        # Compound moves
        compounds: dict[str, list[str]] = {
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

        if base in compounds:
            sub_moves = compounds[base]
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
            raise ValueError(f"Unknown move: {move_str!r}")

        if is_double:
            _apply_cw(self.faces, base)
            _apply_cw(self.faces, base)
        elif is_prime:
            _apply_ccw(self.faces, base)
        else:
            _apply_cw(self.faces, base)

    def apply(self, algorithm: str) -> None:
        """Parse and apply an algorithm string."""
        for token in parse_algorithm(algorithm):
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


def _invert_token(token: str) -> str:
    """Invert a single move token: R→R', R'→R, R2→R2."""
    if token.endswith("'"):
        return token[:-1]
    if token.endswith("2"):
        return token
    return token + "'"


def diagram_to_sim(face: str, a: int, b: int) -> tuple[str, int, int]:
    """Convert diagram (face, a, b) to simulator (face, row, col)."""
    if face == "U":
        return ("U", b, a)
    elif face == "F":
        return ("F", 2 - b, a)
    elif face == "R":
        return ("R", 2 - b, 2 - a)
    raise ValueError(f"Unknown visible face: {face!r}")


_TOKEN_RE = re.compile(r"[RLUDFBMSExyz][w]?[2']?|[rudfb][2']?|\(|\)|×\d+")


def parse_algorithm(alg: str) -> list[str]:
    """Parse an algorithm string into move tokens.

    Supports: R U R' U' R2, lowercase wide (r, f), parenthesized repeats (R U)×2.
    Strips parentheses that aren't followed by a repeat count.
    """
    tokens = _TOKEN_RE.findall(alg)
    result: list[str] = []
    group: list[str] | None = None

    for tok in tokens:
        if tok == "(":
            group = []
        elif tok == ")":
            # Group ends — look for ×N in next token
            continue
        elif tok.startswith("×") and group is not None:
            count = int(tok[1:])
            result.extend(group * count)
            group = None
        elif group is not None:
            group.append(tok)
        else:
            result.append(tok)

    # If group was opened but not repeated, just append
    if group is not None:
        result.extend(group)

    return result
