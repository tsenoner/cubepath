"""Printable credit-card cheat sheet, generated from the canonical alg data.

Emits one double-sided ID-1 card (85.6 x 53.98 mm) carrying the complete
2-Look CFOP last layer on the front and notation, the pre-last-layer steps and
the 4x4/5x5 exception set on the back — plus ready-to-print A4/Letter sheets
and a no-duplex fold-over version. Run via `uv run cubepath-cheatcards`.

Nothing here retypes an algorithm. Every 3x3 string comes from `algs.py` via
`notation.CHUNKS`; every big-cube string is read out of the app script that
pins it for CI. Colour is derived by exact-token lookup in `palette.FAMILY`,
never assigned by hand.

Three failure modes this module actively guards, because each one silently
ships a wrong card:

*   Typst's smart quotes rewrite every ASCII prime to U+2019, which cubing.js
    refuses to parse — `#set smartquote(enabled: false)` plus a gate.
*   Typst exits 0 on an unknown font family, so a macOS-only font compiles
    clean here and falls back to something else everywhere else — the build
    runs `--ignore-system-fonts` and treats warnings as errors.
*   Typst silently paginates on overflow, so a too-full card becomes a third
    page instead of an error — the build asserts the page count and geometry.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from cubepath.algs import ALGORITHMS
from cubepath.notation import (
    BIGCUBE_CHUNKS,
    CHUNKS,
    PARITY_DIFF_4X4,
    PARITY_DIFF_5X5,
    Chunk,
    bigcube_algs,
    block_compactable,
    compact,
    family,
)
from cubepath.palette import TRIGGER_COLORS

_REPO = Path(__file__).resolve().parents[4]
_GUIDE = _REPO / "guide"
_FIGS = _GUIDE / "figures" / "generated"
_OUT = _GUIDE / "build"
_CARD_SVG = _OUT / "card-svg"

CARD_W, CARD_H = 85.6, 53.98  # ISO/IEC 7810 ID-1 — 53.98, not 54
MARGIN = 2.0
USABLE_W, USABLE_H = CARD_W - 2 * MARGIN, CARD_H - 2 * MARGIN

# ── Print-variant diagrams ────────────────────────────────────────────
# The app is backlit and the guide is read on paper at full size; the card is
# 4.65 mm wide and often printed in black and white. #FFD500 on #C0C0C0 is a
# 1.29:1 contrast ratio — ten identical grey squares on a mono printer. These
# substitutions are card-only; diagrams.py is untouched.
_SVG_SUBS: list[tuple[str, str]] = [
    ('fill="#C0C0C0"', 'fill="#5F5F5F"'),
    ('stroke-width="1.5"', 'stroke-width="3.2"'),
    ('stroke-width="1"', 'stroke-width="2.4"'),
    ('stroke-width="2"', 'stroke-width="4.5"'),
]


def build_print_svgs() -> dict[str, int]:
    """Rewrite the OLL/PLL diagrams for greyscale print. Returns hit counts."""
    if _CARD_SVG.exists():
        shutil.rmtree(_CARD_SVG)
    counts = dict.fromkeys((old for old, _ in _SVG_SUBS), 0)
    for sub in ("oll", "pll"):
        dst = _CARD_SVG / sub
        dst.mkdir(parents=True, exist_ok=True)
        for svg in sorted((_FIGS / sub).glob("*.svg")):
            text = svg.read_text()
            for old, new in _SVG_SUBS:
                counts[old] += text.count(old)
                text = text.replace(old, new)
            (dst / svg.name).write_text(text)
    # A future diagrams.py edit must not turn the contrast fix into a no-op.
    for old, n in counts.items():
        if n == 0:
            raise AssertionError(
                f"print-variant SVG rewrite matched nothing for {old!r} — "
                "diagrams.py changed; re-derive the substitutions"
            )
    return counts


# ── Typst rendering of an algorithm ───────────────────────────────────

_COLOR_FN = {"r": "r", "g": "g", "b": "b"}


def _prime(text: str) -> str:
    """Bind each prime to its move letter. `pr()` (not `pr`) so the call ends
    the identifier — `#prU` would parse as a variable named `prU`."""
    return text.replace("'", "#pr()")


def _segment(seg: str, compacted: bool) -> str:
    text = _prime(compact(seg) if compacted else seg)
    fn = _COLOR_FN.get(family(seg) or "")
    return f"#{fn}[{text}]" if fn else text


def _chunk(chunk: Chunk, compacted: bool) -> str:
    joiner = "" if compacted else " "
    body = joiner.join(_segment(s, compacted) for s in chunk)
    return f"[{body}]"


def alg(chunks: list[Chunk], compacted: bool = True, size: str = "AS") -> str:
    """Typst call rendering one algorithm as gap-separated chunks."""
    return f"#a({size}, {', '.join(_chunk(c, compacted) for c in chunks)})"


def key_alg(name: str, **kw) -> str:
    return alg(CHUNKS[name], **kw)


def _esc(s: str) -> str:
    """Escape Typst markup characters in prose."""
    return s.replace("#", "\\#").replace("@", "\\@").replace("*", "\\*")


# ── Card content ──────────────────────────────────────────────────────
# (diagram, name, recognition cue, algorithm key[, rotate])
Row = tuple[str, str, str, str] | tuple[str, str, str, str, int]

OLL_CROSS: list[Row] = [
    ("oll/oll_line.svg", "Line", "bar horizontal", "F-sexy-F'"),
    # The Hook diagram is drawn at the Phase-1 angle (L back-left); the f-alg
    # needs the 180-rotated hold, exactly as the guide does.
    ("oll/oll_hook.svg", "Hook", "L at front-right", "f-sexy-f'", 180),
]

OLL_CORNERS: list[Row] = [
    ("oll/oll_sune.svg", "Sune", "1 yellow, rest CW", "Sune"),
    ("oll/oll_antisune.svg", "Anti-Sune", "1 yellow, rest CCW", "Anti-Sune"),
    ("oll/oll_pi.svg", "Pi", "0 yellow, lights left", "Pi"),
    ("oll/oll_headlights.svg", "Headlights", "2 yellow, lights back", "Headlights"),
    ("oll/oll_double_headlights.svg", "2x Headlights", "0 yellow, lights L+R", "Double Headlights"),
    ("oll/oll_chameleon.svg", "Chameleon", "2 yellow adjacent", "Chameleon"),
    ("oll/oll_bowtie.svg", "Bowtie", "2 yellow diagonal", "Bowtie"),
]

PLL_CORNERS: list[Row] = [
    ("pll/pll_tperm.svg", "T", "headlights on ONE face -- hold LEFT", "T-Perm"),
    ("pll/pll_yperm.svg", "Y", "no headlights -- diagonal swap", "Y-Perm"),
]

PLL_EDGES: list[Row] = [
    ("pll/pll_ub.svg", "Ub", "front edge goes LEFT", "Ub"),
    ("pll/pll_ua.svg", "Ua", "front edge goes RIGHT", "Ua"),
    ("pll/pll_hperm.svg", "H", "opposite edges swap", "H-Perm"),
    ("pll/pll_zperm.svg", "Z", "adjacent edges swap", "Z-Perm"),
]

PHASE1: list[tuple[str, str, str]] = [
    ("white corners", "", "righty / lefty -- corner above its slot, repeat until it drops in"),
    (
        "middle, to right",
        "Edge Insert Right",
        "yellow-free edge on top, colour matched to a centre",
    ),
    ("middle, to left", "Edge Insert Left", "mirror of the row above"),
    ("Niklas", "Niklas", "swaps a corner+edge pair, leaves the yellow face alone"),
]

SHORTCUT: list[tuple[str, str, str]] = [
    (
        "twist corners",
        "Orient Corners Right",
        "yellow sticker faces RIGHT; then U only, next corner to front-right",
    ),
    ("same, other hold", "Orient Corners Front", "yellow sticker faces FRONT"),
]

SITE = "cubepath-six.vercel.app"


def _diagram(svg: str, size: str, rotate: int = 0) -> str:
    return f'dia("{svg}", {size}, rot: {rotate}deg)' if rotate else f'dia("{svg}", {size})'


def _case_rows(rows: list[Row], size: str) -> str:
    out = []
    for row in rows:
        svg, name, cue, key = row[0], row[1], row[2], row[3]
        rot = row[4] if len(row) > 4 else 0
        out.append(
            f"    {_diagram(svg, size, rot)},\n"
            f"      [#nm[{name}] #cue[{_esc(cue)}] \\ {key_alg(key)}],"
        )
    return "\n".join(out)


def _front() -> str:
    left = f"""  #hdr[4][OLL cross][no yellow edge: run both]
  #grid(columns: (D, 1fr), column-gutter: 0.7mm, row-gutter: 0.22mm,
    align: (center + horizon, left + horizon),
{_case_rows(OLL_CROSS, "D")}
  )
  #hdr[5][OLL corners][yellow face]
  #grid(columns: (D, 1fr), column-gutter: 0.7mm, row-gutter: 0.22mm,
    align: (center + horizon, left + horizon),
{_case_rows(OLL_CORNERS, "D")}
  )"""

    right = f"""  #hdr[6][PLL corners][headlights?]
  #grid(columns: (DC, 1fr), column-gutter: 0.8mm, row-gutter: 0.25mm,
    align: (center + horizon, left + horizon),
{_case_rows(PLL_CORNERS, "DC")}
  )
  #hdr[7][PLL edges][put the solved edge at the BACK]
  #grid(columns: (DP, 1fr), column-gutter: 0.8mm, row-gutter: 0.25mm,
    align: (center + horizon, left + horizon),
{_case_rows(PLL_EDGES, "DP")}
  )
  #hdr[][Stuck?][]
  #text(size: 4.0pt, fill: luma(72))[
    Corners not oriented? *Sune* until you see Sune or a solved face. ·
    No headlights? *T* once, then look again. · No solved edge? *Ub* once,
    then re-read. · Nothing matches after any U: opposite colours facing = *H*,
    adjacent = *Z*.]"""

    legend = " ".join(
        f"#sw(C{f.upper()})~#mn[{_prime(compact(t))}]~{label}#h(1.1mm)"
        for f, t, label in (
            ("r", "R U R' U'", "sexy"),
            ("g", "R U R' U", "sune"),
            ("b", "R' F R F'", "sledge"),
        )
    )

    return f"""#let card-front = box(width: {CARD_W}mm, height: {CARD_H}mm, inset: {MARGIN}mm)[
#style(block(width: 100%, height: 100%)[
#grid(columns: (35mm, 1.6mm, 45mm), column-gutter: 0mm, align: (top, center, top),
[
{left}
],
line(length: 100%, angle: 90deg, stroke: 0.35pt + luma(170)),
[
{right}
]
)
#place(bottom + left, dy: -0.45mm, box(width: {USABLE_W}mm, inset: (top: 0.35mm),
  stroke: (top: 0.4pt + luma(160)),
  grid(columns: (1fr, auto), align: (left + horizon, right + horizon),
    text(size: 3.9pt)[{legend} gap = new grip],
    text(size: 3.9pt, weight: "bold")[steps 1--3, 4x4, 5x5 #sym.arrow.r back])))
])]
"""


def _back() -> str:
    bc = bigcube_algs()
    spaced = block_compactable(list(bc.values()))  # False -> the block keeps spaces

    def row3(label: str, alg_markup: str, note: str) -> str:
        return f"  lbl[{_esc(label)}], {alg_markup},\n    cue[{_esc(note)}],"

    p1 = [
        row3(
            PHASE1[0][0],
            f"a(AB, r[{_prime(compact(ALGORITHMS['Sexy Move']))}], [/], "
            f"r[{_prime(compact(ALGORITHMS['Lefty']))}])",
            PHASE1[0][2],
        )
    ]
    for label, key, note in PHASE1[1:]:
        p1.append(row3(label, key_alg(key, size="AB").lstrip("#"), note))

    sc = [
        row3(label, key_alg(key, size="AB").lstrip("#")[:-1] + ", [x2])", note)
        for label, key, note in SHORTCUT
    ]

    def bcalg(name: str) -> str:
        """Markup-context call — keeps its '#', unlike the code-position rows."""
        return alg(BIGCUBE_CHUNKS[name], compacted=spaced, size="AB")

    # The 4x4 line pads its diff token to the width of "3Rw'" so the two parity
    # lines align token-for-token and the single difference is visible.
    oll_p = bcalg("4x4-oll-parity").replace(PARITY_DIFF_4X4, f"#pad[{PARITY_DIFF_4X4}]", 1)
    edge_p = bcalg("5x5-edge-parity").replace(
        PARITY_DIFF_5X5, f"#text(fill: CR)[{PARITY_DIFF_5X5}]", 1
    )

    return f"""#let card-back = box(width: {CARD_W}mm, height: {CARD_H}mm, inset: {MARGIN}mm)[
#style(block(width: 100%, height: 100%)[
#hdr[][Notation][]
#key[R U F L D B = turn that face clockwise · #mn['] = anti-clockwise · #mn[2] = half turn ·
#mn[M] = middle slice (follows L) · #mn[x y z] = turn the whole cube] \\
#key[3x3: #mn[r f] = 2 layers wide · big cubes: #mn[Rw] = 2 layers, #mn[3Rw] = 3 layers,
#mn[2R] = *INNER SLICE ONLY* -- never widen it]

#hdr[1--3][Before the last layer][white on the bottom, yellow on top]
#grid(columns: (14.5mm, 30.5mm, 1fr), column-gutter: 0.8mm, row-gutter: 0.28mm,
  align: (left + horizon, left + horizon, left + horizon),
{chr(10).join(p1)}
)

#hdr[--][Beginner shortcut][use it until you know steps 5--6]
#grid(columns: (14.5mm, 30.5mm, 1fr), column-gutter: 0.8mm, row-gutter: 0.28mm,
  align: (left + horizon, left + horizon, left + horizon),
{chr(10).join(sc)}
)

#hdr[][Big cubes][4x4 & 5x5 -- reduce: 6 centres #sym.arrow.r pair 12 dedges
#sym.arrow.r solve it as a 3x3]
#grid(columns: (14.5mm, 1fr), column-gutter: 0.8mm, row-gutter: 0.28mm,
  align: (left + horizon, left + horizon),
  lbl[last 2 edges], [{bcalg("l2e-flip")} #h(1.2mm)
    #cue[slice out, run it, slice back -- both cubes]],
  lbl[4x4 PLL parity], [{bcalg("4x4-pll-parity")} #h(1.2mm)
    #cue[2 dedges swapped · 50%]],
)
#v(0.25mm)
#cue[*4x4 OLL parity* -- 1 dedge flipped · 50%] \\
{oll_p} \\
#cue[*5x5 edge parity* -- 1 dedge flipped · 50% · #text(fill: CR)[one token] differs;
5x5 has no PLL parity] \\
{edge_p} \\
#cue[Fix parity during the last layer, *before* OLL/PLL -- both parity algs move corners.]

#place(bottom + left, box(width: {USABLE_W}mm, inset: (top: 0.35mm),
  stroke: (top: 0.4pt + luma(160)))[
  #text(size: 4.0pt, fill: luma(60))[
    *Print at 100% / Actual size* -- never "Fit to page". The bar below must measure *80 mm*.
    Sheets, the no-duplex fold-over version and the full print guide:
    *{SITE}/print*] \\
  #v(0.2mm)
  #box(width: 80mm, height: 1.0mm)[
    #place(bottom + left, rect(width: 80mm, height: 0.35mm, fill: luma(40)))
    #place(bottom + left, rect(width: 0.25mm, height: 1.0mm, fill: luma(40)))
    #place(bottom + right, rect(width: 0.25mm, height: 1.0mm, fill: luma(40)))]
])
])]
"""


def _preamble() -> str:
    cr, cg, cb = (TRIGGER_COLORS[k] for k in "rgb")
    return f"""// GENERATED by cubepath-cheatcards — do not edit by hand.
// Every algorithm is expanded from tools/diagrams/src/cubepath/algs.py via
// notation.CHUNKS; every big-cube string is read from the app script that
// pins it for CI. Editing this file will be overwritten on the next build.

#let style(body) = {{
  // Typst rewrites ASCII primes to U+2019, which cubing.js refuses to parse.
  set smartquote(enabled: false)
  set text(font: "Libertinus Serif", size: 4.2pt)
  set par(leading: 0.20em, spacing: 0.20em)
  set block(spacing: 0.30em)
  body
}}

#let M  = "DejaVu Sans Mono"   // the only mono font Typst bundles
#let CR = rgb("#{cr}")
#let CG = rgb("#{cg}")
#let CB = rgb("#{cb}")
// Wider than DejaVu's 0.602em word space, so the gap reads as a break.
#let GAP = 0.90em

// In monospace the prime gets a full character cell, so "R'" reads as two
// separate glyphs with a gap between them. Narrow its advance and pull it
// left so it binds to the letter it modifies.
//
// Measured at 600dpi against DejaVu's own letter spacing: this leaves 0.38mm
// before the prime (tighter than the 0.55mm R->U letter gap, so it binds
// left) and 1.36mm after (matching the 1.31mm U->F gap, so the next move
// starts on normal spacing). Pulling further than -0.24em makes the prime
// touch its letter. Also buys ~19% width back on prime-heavy algorithms
// (Y-Perm: 42.1mm -> 34.2mm).
#let pr() = box(width: 0.22em, move(dx: -0.20em, text("'")))

#let a(sz, ..p) = text(font: M, size: sz, weight: "bold")[#p.pos().join(h(GAP))]
#let r(t) = text(fill: CR, t)
#let g(t) = text(fill: CG, t)
#let b(t) = text(fill: CB, t)
#let dia(f, w, rot: 0deg) = {{
  let i = image("card-svg/" + f, width: w)
  if rot != 0deg {{ box(rotate(rot, i)) }} else {{ i }}
}}
#let hdr(n, t, s) = block(above: 0.5mm, below: 0.35mm)[
  #text(size: 4.8pt, weight: "bold")[#if n != [] [#n#h(0.5mm)]#upper(t)]
  #if s != [] [#text(size: 3.8pt, fill: luma(95))[ · #s]]]
#let nm(t)  = text(size: 4.0pt, weight: "bold")[#t]
#let cue(t) = text(size: 4.0pt, fill: luma(72))[#t]
#let sw(c)  = box(baseline: 0pt, rect(width: 0.9mm, height: 0.9mm, fill: c, stroke: none))
#let mn(t)  = text(font: M, weight: "bold", size: 4.2pt)[#t]
#let key(t) = text(size: 4.0pt, fill: luma(60))[#t]
#let lbl(t) = text(size: 4.1pt, weight: "bold")[#t]
#let D  = 4.65mm   // OLL diagram
#let DP = 6.6mm    // PLL edges — the cycle arrows need the extra size
#let DC = 5.5mm    // PLL corners — headlights is a coarser recognition
#let AS = 6.5pt    // every algorithm, both sides
#let AB = 6.5pt

#let pad(t) = box(width: 5.53mm)[#t]   // measured width of "3Rw'" at 6.5pt
"""


def write_sources() -> Path:
    """Write the shared card body module. Returns its path."""
    _OUT.mkdir(parents=True, exist_ok=True)
    body = _OUT / "card-body.typ"
    body.write_text(_preamble() + "\n" + _front() + "\n" + _back())
    (_OUT / "cheat-card.typ").write_text(
        '#import "card-body.typ": *\n'
        f"#set page(width: {CARD_W}mm, height: {CARD_H}mm, margin: 0pt)\n"
        "#card-front\n#pagebreak()\n#card-back\n"
    )
    return body


# ── Print sheets ──────────────────────────────────────────────────────
# 2 columns x 4 rows of upright ID-1 cards, centred. Because the grid is
# centred and every card on a side is identical, both the long-edge mirror
# (x -> W-x) and the short-edge mirror (y -> H-y) map the slot set onto
# itself: front and back register under *either* duplex setting, so the
# page-2 transform is "do nothing". A 2x5 grid would break that invariance.
SHEETS = {
    "a4": (210.0, 297.0),
    "letter": (215.9, 279.4),
}
COLS, ROWS = 2, 4

_STRIP = (
    "Print at 100% / Actual size -- do NOT fit to page. Two-sided, flip on LONG edge. "
    "This bar must measure exactly 80 mm:"
)


def _sheet(name: str, w: float, h: float) -> str:
    bw, bh = COLS * CARD_W, ROWS * CARD_H
    x0, y0 = (w - bw) / 2, (h - bh) / 2
    xs = [x0 + i * CARD_W for i in range(COLS)]
    ys = [y0 + i * CARD_H for i in range(ROWS)]

    def grid_furniture() -> str:
        parts = []
        # Continuous hairline cut guides across the whole sheet, plus solid
        # ticks reaching into the margins — one straight cut serves four cards.
        for x in xs + [x0 + bw]:
            parts.append(
                f"  #place(top + left, dx: {x}mm, dy: 0mm, "
                f"rect(width: 0.07mm, height: {h}mm, fill: luma(190)))"
            )
            parts.append(
                f"  #place(top + left, dx: {x - 0.05}mm, dy: {y0 - 3}mm, "
                f"rect(width: 0.1mm, height: 3mm, fill: black))"
            )
            parts.append(
                f"  #place(top + left, dx: {x - 0.05}mm, dy: {y0 + bh}mm, "
                f"rect(width: 0.1mm, height: 3mm, fill: black))"
            )
        for y in ys + [y0 + bh]:
            parts.append(
                f"  #place(top + left, dx: 0mm, dy: {y}mm, "
                f"rect(width: {w}mm, height: 0.07mm, fill: luma(190)))"
            )
            parts.append(
                f"  #place(top + left, dx: {x0 - 3}mm, dy: {y - 0.05}mm, "
                f"rect(width: 3mm, height: 0.1mm, fill: black))"
            )
            parts.append(
                f"  #place(top + left, dx: {x0 + bw}mm, dy: {y - 0.05}mm, "
                f"rect(width: 3mm, height: 0.1mm, fill: black))"
            )
        return "\n".join(parts)

    def strip(dy: float) -> str:
        # Duplicated top and bottom so the sheet stays vertically symmetric —
        # that symmetry is what makes short-edge duplex register too.
        return (
            f"  #place(top + left, dx: {x0}mm, dy: {dy}mm, box(width: {bw}mm)[\n"
            f"    #text(size: 7pt)[{_STRIP}]\n"
            f"    #box(width: 80mm, height: 1.4mm)[\n"
            f"      #place(bottom + left, rect(width: 80mm, height: 0.4mm, fill: black))\n"
            f"      #place(bottom + left, rect(width: 0.3mm, height: 1.4mm, fill: black))\n"
            f"      #place(bottom + right, rect(width: 0.3mm, height: 1.4mm, fill: black))]\n"
            f"  ])"
        )

    def face(which: str) -> str:
        cells = [
            f"  #place(top + left, dx: {x}mm, dy: {y}mm, card-{which})" for y in ys for x in xs
        ]
        return "\n".join(cells)

    return f"""#import "card-body.typ": *
#set page(width: {w}mm, height: {h}mm, margin: 0pt)

// front sheet
#[
{grid_furniture()}
{strip(y0 - 9)}
{strip(y0 + bh + 4.5)}
{face("front")}
]
#pagebreak()
// back sheet — no mirroring, no rotation: the centred grid is invariant
// under both the long-edge and short-edge duplex flip.
#[
{grid_furniture()}
{strip(y0 - 9)}
{strip(y0 + bh + 4.5)}
{face("back")}
]
"""


def _foldover(name: str, w: float, h: float) -> str:
    """Single-sided fold-over: back rotated 180 above the front, sharing the
    fold edge. Removes duplex registration error entirely (home duplex carries
    1-2 mm) and works on printers with no duplex at all."""
    panel_h = 2 * CARD_H
    bw, bh = 2 * CARD_W, 2 * panel_h
    x0, y0 = (w - bw) / 2, (h - bh) / 2
    cells = []
    for r in range(2):
        for c in range(2):
            x, y = x0 + c * CARD_W, y0 + r * panel_h
            cells.append(f"  #place(top + left, dx: {x}mm, dy: {y}mm, rotate(180deg, card-back))")
            cells.append(f"  #place(top + left, dx: {x}mm, dy: {y + CARD_H}mm, card-front)")
            cells.append(
                f"  #place(top + left, dx: {x}mm, dy: {y + CARD_H - 0.05}mm, "
                f"rect(width: {CARD_W}mm, height: 0.1mm, fill: luma(150)))"
            )
    return f"""#import "card-body.typ": *
#set page(width: {w}mm, height: {h}mm, margin: 0pt)
#place(top + left, dx: {x0}mm, dy: {y0 - 7}mm, box(width: {bw}mm)[
  #text(size: 7pt)[Print at 100% / Actual size, SINGLE-sided. Score the grey line,
  fold so both printed faces are outward, glue, then cut.]
])
{chr(10).join(cells)}
"""


# ── Build + gates ─────────────────────────────────────────────────────


def _compile(src: Path, pdf: Path) -> None:
    """Compile with only bundled fonts, treating warnings as errors.

    Typst exits 0 on an unknown font family, so a macOS-only font would
    compile clean here and silently fall back everywhere else.
    """
    proc = subprocess.run(
        ["typst", "compile", "--ignore-system-fonts", "--root", str(_GUIDE), str(src), str(pdf)],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.decode() or f"typst failed on {src}")
    if b"warning:" in proc.stderr:
        raise AssertionError(f"typst warnings compiling {src}:\n{proc.stderr.decode()}")


def _pdfinfo(pdf: Path) -> dict[str, str]:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    return dict(
        (k.strip(), v.strip())
        for k, _, v in (line.partition(":") for line in out.splitlines())
        if k
    )


def gate_card(pdf: Path) -> None:
    """Assert the card is exactly two ID-1 pages with parseable algorithms."""
    info = _pdfinfo(pdf)
    if info.get("Pages") != "2":
        raise AssertionError(
            f"cheat card must be exactly 2 pages, got {info.get('Pages')} — "
            "content overflowed and Typst paginated silently"
        )
    want_w, want_h = CARD_W * 72 / 25.4, CARD_H * 72 / 25.4
    m = re.match(r"([\d.]+) x ([\d.]+)", info.get("Page size", ""))
    if not m or abs(float(m.group(1)) - want_w) > 0.1 or abs(float(m.group(2)) - want_h) > 0.1:
        raise AssertionError(f"page size {info.get('Page size')} != {want_w:.3f} x {want_h:.3f} pt")

    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    for bad, label in (("’", "U+2019 right single quote"), ("′", "U+2032 prime")):
        if bad in text:
            raise AssertionError(
                f"{label} found in the PDF — smartquote is rewriting primes and "
                "cubing.js cannot parse the printed algorithms"
            )

    # Every algorithm must appear in the PDF in the form the card prints it.
    # Big-cube algorithms are not compacted (see notation.block_compactable),
    # so they are checked with their spaces stripped rather than removed.
    flat = re.sub(r"\s+", "", text)
    missing = [
        k
        for k, chunks in CHUNKS.items()
        if not all(compact(seg) in flat for chunk in chunks for seg in chunk)
    ]
    missing += [
        k
        for k, chunks in BIGCUBE_CHUNKS.items()
        if not all(re.sub(r"\s+", "", seg) in flat for chunk in chunks for seg in chunk)
    ]
    if missing:
        raise AssertionError(f"algorithms missing from the rendered card: {missing}")

    # Typst function calls must never reach the page as literal text.
    for leak in ("a(AB,", "#a(", "cue[", "lbl["):
        if leak.replace(" ", "") in flat:
            raise AssertionError(f"raw Typst markup {leak!r} rendered as text on the card")


def main() -> None:
    counts = build_print_svgs()
    write_sources()

    pdf = _OUT / "cheat-card.pdf"
    _compile(_OUT / "cheat-card.typ", pdf)
    gate_card(pdf)
    outputs = [pdf]

    for name, (w, h) in SHEETS.items():
        for kind, gen in (("", _sheet), ("-fold", _foldover)):
            src = _OUT / f"cheat-card-{name}{kind}.typ"
            src.write_text(gen(name, w, h))
            out = _OUT / f"cheat-card-{name}{kind}.pdf"
            _compile(src, out)
            outputs.append(out)

    print(f"print-variant SVGs: {sum(counts.values())} substitutions")
    for o in outputs:
        print(f"  {o.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
