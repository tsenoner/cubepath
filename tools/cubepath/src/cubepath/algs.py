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
    # Phase 1 — middle-layer inserts, taught as prose.
    "Edge Insert Right": "U R U R' U' y L' U' L U",
    "Edge Insert Left": "U' L' U' L U y' R U R' U'",
    # Phase 1.5 — the wide-f Hook, plus the two orient-corners finishers that
    # replace Phase 1's "repeat the sexy move and flip the cube". Stored
    # expanded: cubing notation has no repeat operator, and an "x2" suffix
    # would collide with the x rotation the 4x4 parity algorithm contains.
    "f-sexy-f'": "f R U R' U' f'",
    "Orient Corners Right": "R' D' R D R' D' R D",
    "Orient Corners Front": "D' R' D R D' R' D R",
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

# Phase 2 replaces the beginner last-layer order, and three Phase 1 tools stop
# being used the moment it does. The guide counts algorithms LEARNED (22); the
# lessons quote the number in DAILY USE, and that number is this set subtracted
# — derived here so the two can never drift again, which they did: the guide's
# progression table was corrected to 22 and the lesson prose kept saying 18.
#
# Only these three. `Sune` survives the switch with a new job (beginner PE +U
# becomes CFOP OC), and nothing before the last layer changes at all — the
# cross, the first two layers and the yellow cross are solved exactly as
# before, so both edge inserts and both triggers stay in daily use. F2L, which
# finally retires the edge inserts, comes after this milestone, not before it.
RETIRED_AT_CFOP_SWITCH: frozenset[str] = frozenset(
    {
        "Niklas",  # beginner permute-corners → T-Perm (Phase 2), then Y-Perm
        "Orient Corners Right",  # beginner orient-corners → chained Sune, then the 7 OCLL
        "Orient Corners Front",  # same
    }
)


def in_daily_use() -> dict[str, str]:
    """The algorithms still used once the CFOP switch is complete.

    19 of the 22: 15 last-layer (2 OE + 7 OC + 2 PC + 4 PE) plus the four
    first-two-layers tools the switch does not touch.
    """
    return {n: a for n, a in ALGORITHMS.items() if n not in RETIRED_AT_CFOP_SWITCH}


# The Dot cross case is solved by chaining both cross algorithms.
DOT_SEQUENCE = "F R U R' U' F' f R U R' U' f'"
