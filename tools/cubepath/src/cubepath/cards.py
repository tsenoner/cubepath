"""The card deck: what each card says, and the ladder that orders them.

Four panels — three numbered progression cards and one un-numbered annex.
A card exists where the learner's *ability* changes, and after every card they
can still fully solve a cube. That rule is what keeps the set at three: full
OLL and F2L fail it, because their completion cannot be stated as a solve.

Nothing here retypes an algorithm or a recognition cue. Algorithms expand from
`algs.py` / `notation.PLL_CHUNKS`; big-cube strings are read from the app
scripts that pin them for CI; PLL cues come from `recognition.py`, which
derives them from the permutation the diagram is drawn from. Prose is prose,
and `glossary.BANNED` is enforced against the rendered PDF.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from dataclasses import dataclass, field

from cubepath.algs import ALGORITHMS
from cubepath.glossary import gloss_line
from cubepath.notation import (
    BIGCUBE_CHUNKS,
    PARITY_DIFF_4X4,
    PARITY_DIFF_5X5,
    PLL_CHUNKS,
    bigcube_algs,
    block_compactable,
    pll_rows,
)
from cubepath.recognition import pll_cues, sune_fallbacks
from cubepath.typst import alg, diagram, esc, key_alg, prime

# One section of a card face: a bare string spans the card, a pair is the
# two-column layout. `cheatcards._section` renders both.
Section = str | tuple[str, str]

SITE = "cubepath-six.vercel.app"

CARD_W, CARD_H = 85.6, 53.98  # ISO/IEC 7810 ID-1 — 53.98, not 54
MARGIN = 2.0
USABLE_W = CARD_W - 2 * MARGIN
COL_W = 40.2  # 40.2 + 1.2 rule + 40.2 = 81.6


# ── Row helpers ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class Row:
    """One case: a diagram, what to call it, what to look for, what to run.

    `name` and `cue` are prose and get escaped; `body` and `badge` are already
    Typst. Keeping them apart is not fussiness — a badge smuggled into `name`
    has its `#` escaped and prints as literal Typst source on the card.
    """

    svg: str
    name: str
    cue: str
    body: str
    rot: int = 0
    badge: str = ""


def _rows(items: list[Row], size: str, gutter: float = 0.7) -> str:
    """A diagram-and-algorithm grid: one case per row."""
    cells = []
    for it in items:
        head = f"#nm[{esc(it.name)}]" + (f" {it.badge}" if it.badge else "")
        cue_txt = f" #cue[{esc(it.cue)}]" if it.cue else ""
        cells.append(f"    {diagram(it.svg, size, it.rot)},\n      [{head}{cue_txt} \\ {it.body}],")
    return (
        f"#grid(columns: ({size}, 1fr), column-gutter: {gutter}mm, row-gutter: 0.25mm,\n"
        f"  align: (center + horizon, left + horizon),\n" + "\n".join(cells) + "\n)"
    )


def _hdr(title: str, sub: str = "", num: str = "") -> str:
    return f"#hdr[{num}][{esc(title)}][{esc(sub) if sub else ''}]"


def _cue(text: str) -> str:
    return f"#cue[{esc(text)}]"


def _key(text: str) -> str:
    return f"#key[{esc(text)}]"


def _stack(*parts: str) -> str:
    """Join blocks with a blank line so each stays its own paragraph.

    A single newline between two `#cue[...]` calls makes Typst run them into
    one paragraph — four separate on-ramp instructions become a wall of prose.
    """
    return "\n\n".join(p for p in parts if p)


def _words(*terms: str) -> str:
    return _hdr("Words") + "\n\n" + _cue(gloss_line(*terms))


# ── CARD 1 — FIRST SOLVE ──────────────────────────────────────────────

_C1_CORNERS = [
    Row("steps/corner_right.svg", "white sticker RIGHT", "", key_alg("Sexy Move")),
    Row("steps/corner_front.svg", "white sticker FRONT", "", key_alg("Lefty")),
    Row(
        "steps/corner_up.svg",
        "white sticker UP",
        "run the first one once to knock it out, then look again",
        key_alg("Sexy Move"),
    ),
]

_C1_EDGES = [
    Row("steps/edge_right.svg", "goes RIGHT", "", key_alg("Edge Insert Right")),
    Row("steps/edge_left.svg", "goes LEFT", "", key_alg("Edge Insert Left")),
]

_C1_CROSS = [
    Row("oll/oll_dot.svg", "Dot", "no yellow edge at all", key_alg("F-sexy-F'")),
    Row(
        "oll/oll_hook.svg",
        "Hook",
        "two at a right angle: hold them BACK and LEFT",
        key_alg("F-sexy-F'"),
    ),
    Row("oll/oll_line.svg", "Line", "hold the bar left-to-right", key_alg("F-sexy-F'")),
]

_C1_MATCH = [
    Row(
        "steps/align_adjacent.svg",
        "two matched, side by side",
        "hold them BACK and LEFT",
        key_alg("Sune"),
    ),
    Row(
        "steps/align_diagonal.svg",
        "two matched, opposite",
        "run it once from any hold, then look again",
        key_alg("Sune"),
    ),
]

_C1_PLACE = [
    # FRONT-LEFT, not front-right: Niklas fixes the FL corner and 3-cycles the
    # other three. The guide says the same ("Keeps front-left, cycles rest") and
    # `corner_cycle.svg` draws FL as the solved one — the card was the outlier,
    # and holding the solved corner front-right feeds it into the cycle.
    # `test_cards.py` derives the fixed corner and pins this wording to it.
    Row("steps/corner_cycle.svg", "one corner home", "hold it FRONT-LEFT", key_alg("Niklas")),
    # No rotation here: `corner_cycle` is a 3D isometric drawing, so a 180deg
    # turn does not re-orient the case the way it does for a top-down OLL plan
    # view (see the Hook row on Card 2) — it just prints the cube upside down,
    # yellow face underneath. The cue for this row is "from any hold" anyway,
    # so there is no orientation to convey.
    Row(
        "steps/corner_cycle.svg",
        "no corner home",
        "run it once from any hold, then look again",
        key_alg("Niklas"),
    ),
]


def _twice(key: str) -> str:
    """An algorithm printed once with a literal x2 — the stored string is the
    doubled token stream, so this is a label, not a second algorithm."""
    return key_alg(key, extra="x2")


_C1_TWIST = [
    Row("steps/orient_right.svg", "yellow faces RIGHT", "", _twice("Orient Corners Right")),
    Row("steps/orient_front.svg", "yellow faces FRONT", "", _twice("Orient Corners Front")),
]


def card1_front() -> list[Section]:
    left = _stack(
        _cue(f"New here? Do the walkthrough once at {SITE}/learn. This card is the memory jog."),
        _hdr("Notation"),
        _key("R U F L D B = turn that face clockwise, looking at it from outside the cube."),
        _key(
            "' = counter-clockwise. 2 = half turn. Lowercase r f = that face plus the "
            "layer behind it, turning together."
        ),
        _key("y = spin the whole cube left, white staying down. A whole-cube turn solves nothing."),
        _words("algorithm", "trigger"),
        _hdr("White cross", "", "1"),
        f"#align(center)[#{diagram('steps/step_1_cross.svg', '8.0mm')}]",
        _cue(
            "White center DOWN. Bring the four white edges to it. Each edge's side "
            "color must match the center it touches. No algorithm — work it out."
        ),
        _cue(
            "Can't see it? Build the four white edges on the YELLOW face first, each "
            "above its matching center, then turn each one down 180 degrees."
        ),
    )
    right = _stack(
        _hdr("White corners", "", "2"),
        _cue(
            "Find a white corner on top, turn U until it sits above the empty slot it "
            "belongs in, then match a picture below and repeat until it drops in."
        ),
        _rows(_C1_CORNERS, "DS"),
        _hdr("Middle edges", "", "3"),
        _cue(
            "Top edge with NO yellow: turn U until its front color matches the center "
            "under it. The arrow shows which slot it goes to."
        ),
        _rows(_C1_EDGES, "DS"),
        _cue("Edge stuck in the wrong slot? Run either one to kick it out, then place it."),
    )
    return [(left, right)]


def card1_back() -> list[Section]:
    left = _stack(
        _hdr("Yellow cross", "yellow edges only — ignore the corners", "4"),
        _rows(_C1_CROSS, "D"),
        _cue("One algorithm, up to three times: dot to hook to line to cross."),
        _hdr("Match the yellow edges", "", "5"),
        _cue(
            "First turn U so at least two top edges match the center under them. This "
            "algorithm is called Sune; you use it on every card after this one."
        ),
        _rows(_C1_MATCH, "DS"),
    )
    right = _stack(
        _hdr("Put the yellow corners home", "", "6"),
        _rows(_C1_PLACE, "DS"),
        _cue(
            "This cycles the other three corners into place. It also twists the "
            "yellow face you just built — expected, the next step rebuilds it."
        ),
        _hdr("Twist the yellow corners", "", "7"),
        _rows(_C1_TWIST, "DS"),
        _cue(
            "Between corners turn ONLY the top face, to bring the next unsolved "
            "corner to front-right. Never turn the whole cube."
        ),
        _cue(
            "The cube will look destroyed while you do this. Keep going — the last "
            "top turn brings it back."
        ),
    )
    return [(left, right)]


# ── CARD 2 — TWO-LOOK ─────────────────────────────────────────────────

_SUNES = sune_fallbacks()


def _badge(case: str) -> str:
    return f"#bdg[{_SUNES[case]}]"


_C2_CROSS = [
    Row("oll/oll_line.svg", "Line", "bar left-to-right", key_alg("F-sexy-F'")),
    Row("oll/oll_hook.svg", "Hook", "hook pointing front-right", key_alg("f-sexy-f'"), 180),
]

_C2_OLL_A = [
    Row(
        "oll/oll_sune.svg",
        "Sune",
        "1 yellow, rest clockwise",
        key_alg("Sune"),
        badge=_badge("Sune"),
    ),
    Row(
        "oll/oll_antisune.svg",
        "Anti-Sune",
        "1 yellow, rest counter-clockwise",
        key_alg("Anti-Sune"),
        badge=_badge("Anti-Sune"),
    ),
    Row("oll/oll_pi.svg", "Pi", "0 yellow, headlights left", key_alg("Pi"), badge=_badge("Pi")),
]

_C2_OLL_B = [
    Row(
        "oll/oll_headlights.svg",
        "Headlights",
        "2 yellow, headlights at the back",
        key_alg("Headlights"),
        badge=_badge("Headlights"),
    ),
    Row(
        "oll/oll_double_headlights.svg",
        "2x Headlights",
        "0 yellow, headlights both sides",
        key_alg("Double Headlights"),
        badge=_badge("Double Headlights"),
    ),
    Row(
        "oll/oll_chameleon.svg",
        "Chameleon",
        "2 yellow next to each other",
        key_alg("Chameleon"),
        badge=_badge("Chameleon"),
    ),
    Row(
        "oll/oll_bowtie.svg",
        "Bowtie",
        "2 yellow diagonal",
        key_alg("Bowtie"),
        badge=_badge("Bowtie"),
    ),
]

_C2_PLL_CORNERS = [
    Row(
        "pll/pll_tperm.svg", "T", "headlights on ONE face — hold that face LEFT", key_alg("T-Perm")
    ),
    Row(
        "pll/pll_yperm.svg",
        "Y",
        "no headlights — the two swapping corners sit diagonally",
        key_alg("Y-Perm"),
    ),
]

_C2_PLL_EDGES = [
    Row("pll/pll_ub.svg", "Ub", "the front edge travels LEFT", key_alg("Ub")),
    Row("pll/pll_ua.svg", "Ua", "the front edge travels RIGHT", key_alg("Ua")),
    Row("pll/pll_hperm.svg", "H", "both pairs swap straight across", key_alg("H-Perm")),
    Row("pll/pll_zperm.svg", "Z", "each pair swaps with its neighbour", key_alg("Z-Perm")),
]


def card2_front() -> list[Section]:
    left = _stack(
        _hdr("OLL cross", "yellow edges"),
        _rows(_C2_CROSS, "DS"),
        _hdr("OLL corners", "yellow face"),
        _rows(_C2_OLL_A, "DS"),
        _cue("No yellow edge at all? Run the first one, then read again."),
    )
    right = _stack(
        _hdr("OLL corners", "continued"),
        _rows(_C2_OLL_B, "DS"),
        _hdr("Fallback"),
        _cue(
            "The badge on each row is your fallback: that many Sunes, with a U turn "
            "between, also finishes the case. Machine-checked; three is the worst."
        ),
        _cue("Top not all yellow and nothing matches? Run Sune and read again."),
    )
    return [(left, right)]


def card2_back() -> list[Section]:
    left = _stack(
        _hdr("PLL corners", "headlights = two matching corners on one face"),
        _rows(_C2_PLL_CORNERS, "DC"),
        _hdr("PLL edges", "corners home, top still not solved"),
        _rows(_C2_PLL_EDGES, "DP"),
    )
    right = _stack(
        _hdr("Start here", "two new algorithms finish any last layer"),
        # The one algorithm this card names in prose rather than in a row, so
        # it expands from algs.py like every other one — a retyped copy here
        # is the one place on the set nothing would have caught.
        _cue(f"Yellow cross: {ALGORITHMS["F-sexy-F'"]} until the cross appears — at most 3."),
        _cue("Yellow face: Sune, read again, repeat — at most 3 (see the badges)."),
        _cue("Corners: T-Perm. No headlights to hold left? Run it twice."),
        _cue("Edges: Ub. No solved edge to put at the back? Run it twice."),
        _cue(
            "Each case on the front replaces one repeat with one run. Three a week; "
            "you can solve the whole time."
        ),
        _hdr("H vs Z"),
        # NOT a corner cue: recognition.corner_facts derives "all 4 headlights"
        # for BOTH cases, under every AUF. The old wording ("two faces matched,
        # two not = Z") is never true, so every Z read as an H. The edge is
        # what separates them, which is exactly what Card 3's derived cue says.
        _cue(
            "Both show headlights on all four faces. The edge between them decides: "
            "it belongs to the opposite face = H, to a neighbour = Z."
        ),
        _hdr("Stuck?"),
        _cue(
            "Corners home but nothing solves? Turn the top face once and read again — "
            "that is often the whole fix."
        ),
        _cue(
            "One case has beaten you five times? Park it, use its fallback above, "
            "come back next week."
        ),
        _cue(
            "A single piece looks twisted and no algorithm touches it? The cube was "
            "reassembled wrong. Pop it out and reseat it."
        ),
        _words("OLL", "PLL", "headlights", "AUF"),
    )
    return [(left, right)]


# ── CARD 3 — ONE-LOOK PLL ─────────────────────────────────────────────
# Rows are built from the deck, so a case can never be listed with another
# case's algorithm, cue or diagram.

_OWNED_MARK = "●"

# The four blocks Card 3 prints, in reading order. The card tells the learner
# "learn in the printed order", so the printed order *is* the learning order —
# a second hand-written list beside it said Ga..Gd came last when the card puts
# them mid-front, and nothing could catch the disagreement.
_C3_ADJACENT_A = ["T", "Ja", "Jb", "Aa", "Ab", "F"]
_C3_ADJACENT_B = ["Ra", "Rb", "Ga", "Gb", "Gc", "Gd"]
_C3_EDGES = ["Ua", "Ub", "H", "Z"]
_C3_DIAGONAL = ["Y", "V", "Na", "Nb", "E"]
_C3_PRINTED = _C3_ADJACENT_A + _C3_ADJACENT_B + _C3_EDGES + _C3_DIAGONAL


@functools.cache
def pll_deck() -> dict[str, Row]:
    """name -> the printed row, for all 21 cases."""
    cues = pll_cues()
    out = {}
    for row in pll_rows():
        owned = row.source == "algs.py"
        label = f"{_OWNED_MARK} {row.name}" if owned else row.name
        out[row.name] = Row(
            svg=f"pll-full/pll_card_{row.name.lower()}.svg",
            name=label,
            cue=cues[row.name],
            body=alg(PLL_CHUNKS[row.name], size="AP"),
        )
    return out


def _pll_rows(names: list[str]) -> str:
    deck = pll_deck()
    return _rows([deck[n] for n in names], "DF", gutter=0.6)


def card3_front() -> list[Section]:
    left = _stack(
        _hdr("Adjacent corner swap", "exactly one face shows headlights"),
        _pll_rows(_C3_ADJACENT_A),
        _cue(
            "One face shows headlights: two corners of that face match. Hold as "
            "drawn, run, then turn the top to finish."
        ),
    )
    right = _stack(
        _hdr("Adjacent corner swap", "continued"),
        _pll_rows(_C3_ADJACENT_B),
        _cue(
            "Learn in the printed order, three a week, about six weeks. Ja and Jb on "
            "the same day — one is the mirror of the other."
        ),
    )
    return [(left, right)]


def card3_back() -> list[Section]:
    left = _stack(
        _hdr("Edges only", "corners already home"),
        _pll_rows(_C3_EDGES),
        _hdr("How to look"),
        _cue(
            "1. Count the headlight faces. One = front of this card. Four = this "
            "column. None = the column on the right."
        ),
        _cue("2. Only then read the edges to pick the exact case."),
        _cue(
            "3. Line the case up as drawn, run it, turn the top again to "
            "finish — that last free turn is the AUF."
        ),
        _cue(f"{_OWNED_MARK} = already yours from Card 2."),
        # The glossary sits in whichever column has room; F13 only requires
        # it to be on the card that uses the terms, not in a fixed place.
        _words("PLL", "headlights", "AUF", "adjacent corner swap", "diagonal corner swap"),
    )
    right = _stack(
        _hdr("Diagonal corner swap", "no headlights anywhere"),
        _pll_rows(_C3_DIAGONAL),
        _hdr("Stuck?"),
        _cue(
            "Case you have not learned? Two-look it from Card 2 — T-Perm then Ub "
            "still solves it. Nothing here can strand you."
        ),
        _cue("Beaten five times by one case? Park it, two-look it, come back next week."),
    )
    return [(left, right)]


# ── CARD A — ANNEX ────────────────────────────────────────────────────


def _mark_move(markup: str, token: str, wrapper: str) -> str:
    """Wrap the first *rendered* occurrence of one move in a Typst call.

    The match has to run on the rendered markup, not the raw token: `prime()`
    has already rewritten `'` to `#pr()`, so searching for `Rw'` found nothing
    and `str.replace` reports that by silently doing nothing. The two parity
    lines shipped unpadded, with no red move on the 5x5 line, while the cue
    above them promised one. Raise instead of shipping the quiet version.
    """
    rendered = prime(token)
    if rendered not in markup:
        raise AssertionError(f"{token!r} renders as {rendered!r}, which is not in {markup!r}")
    return markup.replace(rendered, wrapper.format(rendered), 1)


def _bigcube_block() -> str:
    bc = bigcube_algs()
    # False here means "a layer-count prefix makes compaction ambiguous", so
    # the whole block keeps its real spaces (see notation.block_compactable).
    compacted = block_compactable(list(bc.values()))

    def bcalg(name: str) -> str:
        return alg(BIGCUBE_CHUNKS[name], compacted=compacted, size="AB")

    # The 4x4 line pads its differing move to the width of "3Rw'" so the two
    # parity lines align move-for-move and the single difference is visible.
    oll_p = _mark_move(bcalg("4x4-oll-parity"), PARITY_DIFF_4X4, "#pad[{}]")
    edge_p = _mark_move(bcalg("5x5-edge-parity"), PARITY_DIFF_5X5, "#text(fill: CR)[{}]")
    return f"""{_hdr("Big cubes", "4x4 and 5x5")}
#cue[Reduce: build the 6 centers #sym.arrow.r pair the 12 edges #sym.arrow.r solve it as a 3x3.]
{_key("Rw = 2 layers wide. 3Rw = 3 layers. 2R = 2nd LAYER ONLY — never widen it.")}
#grid(columns: (14.5mm, 1fr), column-gutter: 0.8mm, row-gutter: 0.28mm,
  align: (left + horizon, left + horizon),
  lbl[last 2 edges], [{bcalg("l2e-flip")} #h(1.2mm)
    #cue[slice out, run it, slice back -- both cubes]],
  lbl[4x4 PLL parity], [{bcalg("4x4-pll-parity")} #h(1.2mm)
    #cue[2 edge pairs swapped · half the time]],
)
#v(0.25mm)
#cue[*4x4 OLL parity* -- 1 edge pair flipped · half the time] \\
{oll_p} \\
#cue[*5x5 edge parity* -- 1 edge pair flipped · half the time ·
#text(fill: CR)[one move] differs; 5x5 has no PLL parity] \\
{edge_p} \\
#cue[Fix parity during the last layer, *before* OLL and PLL -- both parity
algorithms move corners.]"""


def annex_front() -> list[Section]:
    """Big cubes run full width. Their algorithms keep real spaces (a
    layer-count prefix makes compaction ambiguous), so an 18-move parity
    algorithm needs the whole card rather than a 40.2 mm column."""
    # The notation overview in card ink: the six face turns with their
    # direction, which is the one thing the prose key cannot say.
    notation = _stack(
        _hdr("Notation"),
        "#grid(columns: (15.5mm, 1fr), column-gutter: 0.8mm, align: (top, top),\n"
        f"  {diagram('notation/overview.svg', '15.5mm')},\n"
        "  ["
        + _stack(
            _key(
                "Each letter turns that face clockwise, seen from outside the cube — "
                "so from your seat L, D and B look counter-clockwise. "
                "' = counter-clockwise. 2 = half turn."
            ),
            _key(
                "M = middle slice, turning the way L turns. x y z = the whole cube, "
                "turning the way R, U and F turn. Lowercase r f = that face plus the "
                "layer behind it, turning together."
            ),
        )
        + "],\n)",
    )
    shortcut = _stack(
        _hdr("Beginner shortcut", "use it until you know Sune"),
        _cue(
            "Twist a yellow corner four turns at a time, turning ONLY the top face between corners."
        ),
        "#grid(columns: (14.5mm, 1fr), column-gutter: 0.8mm, row-gutter: 0.28mm,\n"
        "  align: (left + horizon, left + horizon),\n"
        f"  lbl[yellow faces RIGHT], [{_twice('Orient Corners Right')}],\n"
        f"  lbl[yellow faces FRONT], [{_twice('Orient Corners Front')}],\n)",
    )
    words = _stack(
        _hdr("Words"),
        _cue(
            gloss_line(
                "algorithm",
                "trigger",
                "sexy move",
                "sledgehammer",
                "parity",
                "edge pair",
            )
        ),
    )
    return [_bigcube_block(), (notation, shortcut), words]


def annex_back() -> list[Section]:
    ladder = _stack(
        _hdr("The ladder"),
        _cue("1/3 FIRST SOLVE · 9 algorithms · unlock: five solves, card face down."),
        _cue("2/3 TWO-LOOK · +13 · unlock: fifteen last layers in exactly two algorithms."),
        _cue("3/3 ONE-LOOK PLL · +15 · done: all 21 named, twice on separate days."),
        _cue(
            "After that: full OLL, F2L, cross planning, look-ahead — in the app, not on card stock."
        ),
        _hdr("Why there are only three"),
        _cue(
            "A card is good at a closed set of cases you tell apart by sight. It "
            "is bad at a skill you drill. F2L, cross planning and look-ahead are "
            "drills with no finite case list. Full OLL is 57 cases, 22 of which "
            "differ only in a sliver a fifth of a millimetre wide at this size. "
            "All of them are in the app, with a real cube and randomised setup. "
            "This set stops where the medium stops."
        ),
    )
    words = _stack(
        _hdr("Words"),
        _cue(
            gloss_line(
                "OLL",
                "PLL",
                "Sune",
                "sexy move",
                "sledgehammer",
                "headlights",
                "trigger",
                "AUF",
            )
        ),
        _cue(
            gloss_line(
                "parity",
                "edge pair",
                "F2L",
                "look-ahead",
                "adjacent corner swap",
                "diagonal corner swap",
            )
        ),
    )
    stamp = _stack(
        _hdr("Print and version"),
        _cue(
            "Every ALGORITHM on these cards is expanded from machine-verified data "
            "and checked against a cube simulator at build time; if one were wrong "
            "the build would fail rather than ship. Recognition wording is "
            "generated from the same permutation the diagram is drawn from."
        ),
        _cue(
            f"Set v1.0 · reprint any single card at {SITE}/print · print at 100% / "
            f"Actual size, never 'Fit to page'."
        ),
    )
    return [(ladder, words), stamp]


# ── The deck ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Card:
    index: int
    num: int | None  # None => annex
    slug: str
    title: str
    tint_L: int
    front: Callable[[], list[Section]]
    back: Callable[[], list[Section]]
    unlock: str = ""
    master: str = ""
    supersedes: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ident(self) -> str:
        return f"{self.num}/{TIERS}" if self.num else "A"

    @property
    def next(self) -> Card | None:
        """The next numbered card. The annex is not on the ladder, so it has
        no successor — and is nobody's successor either."""
        if self.num is None:
            return None
        return next((c for c in DECK if c.num == self.num + 1), None)

    @property
    def next_title(self) -> str | None:
        n = self.next
        return f"{n.ident} {n.title.upper()}" if n else None

    @property
    def superseded_by(self) -> str | None:
        """The inverse of `supersedes`. Typing both directions is how the two
        halves of one seam end up disagreeing."""
        return next((c.slug for c in DECK if c.supersedes == self.slug), None)

    @property
    def filled(self) -> int:
        return self.num if self.num else 0


DECK: list[Card] = [
    Card(
        index=0,
        num=1,
        slug="first-solve",
        title="First solve",
        tint_L=78,
        front=card1_front,
        back=card1_back,
        unlock="UNLOCK CARD 2 — five scrambles in a row with this card face down.",
        master="MASTER: those five under 3:00. My target: ______",
        notes=(
            "LAST-LAYER ORDER ON THIS CARD: yellow cross, match edges, place corners, "
            "twist corners. Card 2 replaces this order permanently — it is the only "
            "thing on this card that gets retired.",
        ),
    ),
    Card(
        index=1,
        num=2,
        slug="two-look",
        title="Two-look",
        tint_L=62,
        front=card2_front,
        back=card2_back,
        unlock=(
            "UNLOCK CARD 3 — fifteen last layers in a row, each finished in exactly "
            "two algorithms, case named out loud first. A repeat does not count."
        ),
        master="MASTER: solves averaging under 1:00. My target: ______",
        supersedes="first-solve",
        notes=(
            "THE NEW ORDER: yellow cross, yellow face, corners home, edges home. This never "
            "changes again. Card 1's order is retired, and so is Niklas: it moves corners "
            "but wrecks the yellow face, and here the yellow face is finished first.",
        ),
    ),
    Card(
        index=2,
        num=3,
        slug="one-look-pll",
        title="One-look PLL",
        tint_L=46,
        front=card3_front,
        back=card3_back,
        unlock=(
            "DONE — all twenty-one named correctly, twenty-one in a row, no card in hand, on "
            "two separate days."
        ),
        master="MASTER: PLL under 3 s, solves under 0:30. My target: ______",
        supersedes=None,
        notes=(
            "Card 2 gives you 19/72 last layers in one look. This card gives 71/72.",
            f"Next: the other 57 top-face cases, and the first two layers solved as "
            f"pairs — drilled with a cube in the app: {SITE}/practice",
        ),
    ),
    Card(
        index=3,
        num=None,
        slug="annex",
        title="Annex — big cubes and the map",
        tint_L=88,
        front=annex_front,
        back=annex_back,
        unlock="",
        master="",
        notes=("Not a tier, no unlock, no order. Use it when you buy a 4x4.",),
    ),
]

BY_SLUG = {c.slug: c for c in DECK}

# Duplex imposition: each card occupies both slots of its row. See §5 of
# docs/card-set-plan.md — this is what makes the page-2 transform trivial
# under a long-edge flip and a single whole-page rotation under short-edge.
FRONT_SLOTS: list[int] = [c.index for c in DECK for _ in range(2)]


# How many numbered tiers the ladder has. The annex is not one of them.
TIERS: int = sum(1 for c in DECK if c.num)


def learn_order() -> list[str]:
    """Card 3's printed learning order: the cases it introduces, in the order
    they appear on the card, because that is what the card tells you to do.

    Also the only place that asserts Card 3 lists all 21 exactly once — a case
    dropped from a block would otherwise just quietly not be on the card."""
    names = [r.name for r in pll_rows()]
    assert sorted(_C3_PRINTED) == sorted(names), f"Card 3 does not print all 21: {_C3_PRINTED}"
    owned = {r.name for r in pll_rows() if r.source == "algs.py"}
    return [n for n in _C3_PRINTED if n not in owned]
