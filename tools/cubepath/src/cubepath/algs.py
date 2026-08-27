"""Canonical algorithm set — single source of truth for diagrams, tests, and the guide.

Every algorithm here is machine-verified: diagrams derive their sticker states
from these strings via the simulator, and tests assert the guide's reference
table matches. Editing an algorithm here regenerates its diagram on the next
build; a mismatch with the guide text fails CI.
"""

# name → algorithm. Names match the guide's Algorithm Reference table.
ALGORITHMS: dict[str, str] = {
    # Triggers & Phase 1
    "Sexy Move": "R U R' U'",
    "Lefty": "L' U' L U",
    "F-sexy-F'": "F R U R' U' F'",
    "Sune": "R U R' U R U2 R'",
    "Niklas": "R U' L' U R' U' L",
    # Phase 1 — finishers the guide teaches as prose. Stored expanded:
    # cubing notation has no repeat operator, and an "x2" suffix would collide
    # with the x rotation the 4x4 parity algorithm contains.
    "Orient Corners Right": "R' D' R D R' D' R D",
    "Orient Corners Front": "D' R' D R D' R' D R",
    "Edge Insert Right": "U R U R' U' y L' U' L U",
    "Edge Insert Left": "U' L' U' L U y' R U R' U'",
    # Phase 1.5
    "f-sexy-f'": "f R U R' U' f'",
    # Phase 2
    "T-Perm": "R U R' U' R' F R2 U' R' U' R U R' F'",
    "Ub": "R2 U R U R' U' R' U' R' U R'",
    # Phase 3 — orient corners
    "Anti-Sune": "R U2 R' U' R U' R'",
    "Pi": "f R U R' U' f' F R U R' U' F'",
    "Headlights": "R2 D R' U2 R D' R' U2 R'",
    "Double Headlights": "R U R' U R U' R' U R U2 R'",
    "Chameleon": "r U R' U' r' F R F'",
    "Bowtie": "F' r U R' U' r' F R",
    # Phase 3 — permute corners
    "Y-Perm": "F R U' R' U' R U R' F' R U R' U' R' F R F'",
    # Phase 3 — permute edges
    "Ua": "M2 U M U2 M' U M2",
    "H-Perm": "M2 U' M2 U2 M2 U' M2",
    "Z-Perm": "M' U' M2 U' M2 U' M' U2 M2 U",
}

# The Dot cross case is solved by chaining both cross algorithms.
DOT_SEQUENCE = "F R U R' U' F' f R U R' U' f'"
