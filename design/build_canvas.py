"""Generate the Cubepath design-canvas artboards (.dc.html) from shared tokens.

Run from repo root:  python3 design/build_canvas.py
Working files land in design/ — re-run after edits, then re-seed the canvas.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "design"
GEN = ROOT / "guide" / "figures" / "generated"

sys.path.insert(0, str(ROOT / "tools" / "diagrams" / "src"))
from cubepath.algs import ALGORITHMS  # noqa: E402
from cubepath.cube import Cube, invert_algorithm  # noqa: E402

# ── Tokens (light) ───────────────────────────────────────────────────
T = {
    "paper": "#FCFBF8",
    "card": "#FFFFFF",
    "ink": "#1C1917",
    "soft": "#57534E",
    "faint": "#8A857D",
    "line": "#E7E4DE",
    "accent": "#1565C0",
    "accent_soft": "#E8F4FD",
    "ok": "#2E7D32",
    "ok_soft": "#E8F5E9",
    "warn": "#E65100",
    "warn_soft": "#FFF3E0",
    "brand": "#FFD500",
    "trig_r": "#D32F2F",
    "trig_g": "#2E7D32",
    "trig_b": "#1565C0",
}
# Dark counterparts
D = {
    "paper": "#161412",
    "card": "#1E1B18",
    "ink": "#ECE8E1",
    "soft": "#B3ADA4",
    "faint": "#7D786F",
    "line": "#2E2A26",
    "accent": "#6FAAE8",
    "accent_soft": "#16283C",
    "ok": "#7CC47F",
    "ok_soft": "#16281A",
    "warn": "#F0964C",
    "warn_soft": "#2E2014",
    "brand": "#FFD500",
    "trig_r": "#EF6B62",
    "trig_g": "#7CC47F",
    "trig_b": "#6FAAE8",
}

FONTS = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&amp;"
    "family=IBM+Plex+Sans:wght@400;500;600&amp;"
    'family=IBM+Plex+Mono:wght@500;600&amp;display=swap">'
)


def css(t: dict) -> str:
    return f"""
  body {{ margin: 0; background: {t["paper"]}; color: {t["ink"]};
    font-family: 'IBM Plex Sans', system-ui, sans-serif; font-size: 15px;
    line-height: 1.55; -webkit-font-smoothing: antialiased; }}
  a {{ color: {t["accent"]}; text-decoration: none; }}
  a:hover {{ color: {t["trig_b"]}; text-decoration: underline; }}
  h1, h2, h3 {{ font-family: 'Newsreader', Georgia, serif; margin: 0; font-weight: 600; }}
  h1 {{ font-size: 34px; line-height: 1.15; letter-spacing: -0.01em; }}
  h2 {{ font-size: 23px; line-height: 1.2; }}
  h3 {{ font-size: 17px; line-height: 1.3; }}
  .mono {{ font-family: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    font-weight: 500; }}
  .alg {{ font-family: 'IBM Plex Mono', ui-monospace, Menlo, monospace; font-weight: 600;
    font-size: 14.5px; letter-spacing: 0.01em; white-space: nowrap; }}
  .tr {{ color: {t["trig_r"]}; }} .tg {{ color: {t["trig_g"]}; }} .tb {{ color: {t["trig_b"]}; }}
  .soft {{ color: {t["soft"]}; }} .faint {{ color: {t["faint"]}; }}
  .small {{ font-size: 13px; }} .tiny {{ font-size: 12px; }}
  .card {{ background: {t["card"]}; border: 1px solid {t["line"]}; border-radius: 10px; }}
  .btn {{ display: inline-flex; align-items: center; gap: 8px; border-radius: 8px;
    font-weight: 600; font-size: 14px; padding: 10px 18px; cursor: pointer;
    border: 1px solid transparent; }}
  .btn-primary {{ background: {t["accent"]}; color: #fff; }}
  .btn-secondary {{ background: transparent; color: {t["accent"]};
    border-color: {t["accent"]}; }}
  .btn-ghost {{ background: transparent; color: {t["soft"]}; border-color: {t["line"]}; }}
  .chip {{ display: inline-flex; align-items: center; gap: 6px; border-radius: 999px;
    font-size: 12.5px; font-weight: 600; padding: 3px 10px; }}
  .navlink {{ font-weight: 600; font-size: 14px; color: {t["soft"]}; }}
  .navlink-active {{ color: {t["ink"]}; }}
  .diagram svg {{ display: block; }}
  .wrapalg .alg {{ white-space: normal; line-height: 1.6; }}
"""


def svg_inline(rel: str, size: int) -> str:
    """Inline a generated SVG scaled to `size` px."""
    raw = (GEN / rel).read_text()
    raw = raw[raw.index("<svg") :]
    # force display size, keep viewBox scaling
    raw = raw.replace("<svg ", f'<svg style="width:{size}px;height:{size}px" ', 1)
    for attr in ('width="192px" height="192px"', 'width="220px" height="220px"'):
        raw = raw.replace(attr, "")
    import re

    raw = re.sub(r'\swidth="\d+px"\sheight="\d+px"', " ", raw, count=1)
    return f'<span class="diagram">{raw}</span>'


def cube_mark(px: int = 22) -> str:
    """Tiny 3x3 brand mark in cube yellow."""
    c = px / 3
    cells = "".join(
        f'<rect x="{j * c + 0.75}" y="{i * c + 0.75}" width="{c - 1.5}" height="{c - 1.5}" '
        f'rx="1.5" fill="{T["brand"]}" stroke="#333333" stroke-width="0.9"/>'
        for i in range(3)
        for j in range(3)
    )
    return f'<svg width="{px}" height="{px}" viewBox="0 0 {px} {px}">{cells}</svg>'


def icon(name: str, size: int = 18, color: str = "currentColor") -> str:
    paths = {
        "play": '<path d="M7 5l10 7-10 7z" fill="CUR" stroke="none"/>',
        "check": '<path d="M4 12.5l5 5L20 6.5"/>',
        "chev": '<path d="M9 5l7 7-7 7"/>',
        "book": '<path d="M4 5a2 2 0 0 1 2-2h14v18H6a2 2 0 0 0-2 2z"/><path d="M4 19a2 2 0 0 1 2-2h14"/>',
        "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.5"/>',
        "grid": '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
        "download": '<path d="M12 4v11"/><path d="M7 11l5 5 5-5"/><path d="M5 20h14"/>',
        "repeat": '<path d="M4 9a6 6 0 0 1 10.9-3.4"/><path d="M15 2l1 4-4 1"/><path d="M20 15a6 6 0 0 1-10.9 3.4"/><path d="M9 22l-1-4 4-1"/>',
        "shuffle": '<path d="M4 7h4l8 10h4"/><path d="M18 5l3 2-3 2"/><path d="M4 17h4"/><path d="M14 7h6"/><path d="M18 15l3 2-3 2"/>',
        "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2.5"/>',
        "wifi-off": '<path d="M2 9a15 15 0 0 1 20 0"/><path d="M6 12.5a10 10 0 0 1 12 0"/><circle cx="12" cy="17" r="1.4" fill="CUR" stroke="none"/><path d="M4 4l16 16"/>',
    }
    p = paths[name].replace("CUR", color)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round">{p}</svg>'
    )


def alg_html(alg: str, t: dict) -> str:
    """Render an algorithm with trigger coloring, longest-match first."""
    spans = [
        ("R U R' U'", "tr"),
        ("R U R' U", "tg"),
        ("R' F R F'", "tb"),
        ("F R F'", "tb"),
    ]
    out, rest = [], alg
    while rest:
        hit = None
        for pat, cls in spans:
            if rest.startswith(pat) and (len(rest) == len(pat) or rest[len(pat)] == " "):
                hit = (pat, cls)
                break
        if hit:
            out.append(f'<span class="{hit[1]}">{hit[0]}</span>')
            rest = rest[len(hit[0]) :].lstrip()
        else:
            tok, _, rest = rest.partition(" ")
            out.append(tok)
            rest = rest.lstrip()
    return f'<span class="alg">{" ".join(out)}</span>'


def header(t: dict, active: str = "Learn") -> str:
    links = "".join(
        f'<span class="navlink{" navlink-active" if n == active else ""}">{n}</span>'
        for n in ("Learn", "Practice", "Reference")
    )
    return f"""
<div style="display: flex; align-items: center; gap: 28px; padding: 14px 36px;
    border-bottom: 1px solid {t["line"]}; background: {t["card"]}">
  <div style="display: flex; align-items: center; gap: 10px">
    {cube_mark(20)}
    <span style="font-family: 'Newsreader', Georgia, serif; font-size: 21px;
      font-weight: 700; letter-spacing: -0.01em">cubepath</span>
  </div>
  <div style="display: flex; gap: 22px">{links}</div>
  <div style="flex-grow: 1"></div>
  <span class="chip" style="background: {t["ok_soft"]}; color: {t["ok"]}">{icon("wifi-off", 13, t["ok"])} Available offline</span>
  <span class="chip" style="background: {t["accent_soft"]}; color: {t["accent"]}">{icon("download", 13, t["accent"])} Install</span>
</div>"""


def progress(t: dict, pct: int, w: str = "100%") -> str:
    return (
        f'<div style="width: {w}; height: 5px; border-radius: 3px; background: {t["line"]}">'
        f'<div style="width: {pct}%; height: 5px; border-radius: 3px; background: '
        f'{t["ok"] if pct else t["line"]}"></div></div>'
    )


def wrap(body: str, t: dict, width: int) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  {FONTS}
  <style>{css(t)}</style>
</helmet>
<div style="width: {width}px; min-height: 100%; background: {t["paper"]}">
{body}
</div>
</x-dc>
<script data-dc-script data-props='{{}}'>
class Component extends DCLogic {{
  renderVals() {{ return {{}}; }}
}}
</script>
</body>
</html>
"""


# ── Case data (real guide content) ───────────────────────────────────
OC_CASES = [
    ("oll/oll_antisune.svg", "Anti-Sune", "1 yellow corner, others CCW", ALGORITHMS["Anti-Sune"]),
    ("oll/oll_pi.svg", "Pi", "0 yellow — headlights left only", ALGORITHMS["Pi"]),
    ("oll/oll_headlights.svg", "Headlights", "2 yellow at back, headlights facing you", ALGORITHMS["Headlights"]),
    ("oll/oll_double_headlights.svg", "Double Headlights", "0 yellow — headlights left + right", ALGORITHMS["Double Headlights"]),
    ("oll/oll_chameleon.svg", "Chameleon", "2 adjacent yellow (right)", ALGORITHMS["Chameleon"]),
    ("oll/oll_bowtie.svg", "Bowtie", "2 diagonal yellow", ALGORITHMS["Bowtie"]),
]

# Verified T-Perm drill scramble (inverse of the alg) — asserted below.
TPERM_SCRAMBLE = invert_algorithm(ALGORITHMS["T-Perm"])
_c = Cube.solved()
_c.apply(TPERM_SCRAMBLE)
_c.apply(ALGORITHMS["T-Perm"])
assert _c.is_solved(), "T-Perm scramble broken"


def case_row(t: dict, svg_rel: str, name: str, recog: str, alg: str, learned: bool) -> str:
    status = (
        f'<span class="chip" style="background: {t["ok_soft"]}; color: {t["ok"]}">{icon("check", 12, t["ok"])} Learned</span>'
        if learned
        else f'<span class="chip" style="background: {t["paper"]}; color: {t["faint"]}; border: 1px solid {t["line"]}">Learning</span>'
    )
    return f"""
  <div style="display: flex; align-items: center; gap: 18px; padding: 14px 18px;
      border-top: 1px solid {t["line"]}">
    {svg_inline(svg_rel, 62)}
    <div style="display: flex; flex-direction: column; gap: 3px; width: 240px">
      <span style="font-weight: 600; font-size: 15.5px">{name}</span>
      <span class="small soft">{recog}</span>
    </div>
    <div style="flex-grow: 1">{alg_html(alg, t)}</div>
    {status}
    <span style="display: inline-flex; width: 38px; height: 38px; border-radius: 8px;
      background: {t["accent_soft"]}; color: {t["accent"]}; align-items: center;
      justify-content: center">{icon("play", 17, t["accent"])}</span>
  </div>"""


def player_frame(t: dict, iso_svg: str, alg: str, caption: str) -> str:
    ticks = "".join(
        f'<div style="flex-grow: 1; height: 4px; border-radius: 2px; background: '
        f'{t["accent"] if i < 5 else t["line"]}"></div>'
        for i in range(12)
    )
    return f"""
  <div class="card" style="padding: 20px; display: flex; flex-direction: column; gap: 14px">
    <div style="display: flex; align-items: center; justify-content: center; padding: 8px;
        background: {t["paper"]}; border-radius: 8px">{svg_inline(iso_svg, 190)}</div>
    <div style="display: flex; align-items: center; gap: 10px">
      <span style="display: inline-flex; width: 34px; height: 34px; border-radius: 50%;
        background: {t["accent"]}; color: #fff; align-items: center;
        justify-content: center">{icon("play", 15, "#fff")}</span>
      <div style="display: flex; flex-grow: 1; gap: 3px">{ticks}</div>
      <span class="tiny mono soft">5 / 14</span>
    </div>
    <div style="text-align: center">{alg_html(alg, t)}</div>
    <div style="display: flex; justify-content: center; gap: 8px">
      <span class="chip btn-ghost" style="border: 1px solid {t["line"]}; color: {t["soft"]}">{icon("repeat", 12, t["soft"])} Loop</span>
      <span class="chip" style="border: 1px solid {t["line"]}; color: {t["soft"]}">0.5×</span>
      <span class="chip" style="border: 1px solid {t["line"]}; color: {t["soft"]}">1×</span>
    </div>
    <span class="tiny faint" style="text-align: center">{caption}</span>
  </div>"""


# ── Artboards ────────────────────────────────────────────────────────


def build_main(t: dict) -> str:
    courses = [
        ("3×3 Beginner", "Solve the cube reliably — 7 steps, one trigger.", "12 lessons", 100),
        ("Speed Tricks", "Cross on bottom, wide-f Hook, no-flip corners.", "3 lessons", 100),
        ("2-Look CFOP", "The CFOP switch — +12 algorithms, no dead zone.", "8 lessons", 60),
        ("Full CFOP", "Intuitive F2L, full OLL & PLL — 119 cases.", "26 lessons", 0),
        ("4×4", "Your 3×3 + two new skills + parity.", "6 lessons", 0),
        ("5×5", "Freeslice pairing + last two edges.", "5 lessons", 0),
    ]
    cards = ""
    for i, (name, blurb, count, pct) in enumerate(courses):
        state = (
            f'<span class="chip" style="background: {t["ok_soft"]}; color: {t["ok"]}">{icon("check", 12, t["ok"])} Done</span>'
            if pct == 100
            else (
                f'<span class="chip" style="background: {t["accent_soft"]}; color: {t["accent"]}">Continue</span>'
                if pct
                else f'<span class="chip" style="color: {t["faint"]}; border: 1px solid {t["line"]}">Not started</span>'
            )
        )
        cards += f"""
    <div class="card" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 10px">
      <div style="display: flex; align-items: center; gap: 10px">
        <span class="mono" style="font-size: 13px; color: {t["faint"]}">{i + 1:02d}</span>
        <h3 style="flex-grow: 1">{name}</h3>
        {state}
      </div>
      <span class="small soft">{blurb}</span>
      <div style="display: flex; align-items: center; gap: 12px">
        {progress(t, pct, "70%")}
        <span class="tiny faint">{count}</span>
      </div>
    </div>"""
    reviews = "".join(
        f"""<div style="display: flex; align-items: center; gap: 10px; padding: 8px 0;
        border-top: 1px solid {t["line"]}">
      <span style="font-weight: 600; font-size: 14px; width: 130px">{n}</span>
      <span class="tiny faint" style="flex-grow: 1">{d}</span>
      </div>"""
        for n, d in [("T-Perm", "due now"), ("Ua", "due now"), ("Pi", "due in 2 h"),
                     ("Double Headlights", "due in 5 h"), ("Z-Perm", "due today"), ("Y-Perm", "due today")]
    )
    return f"""
{header(t, "Learn")}
<div style="display: flex; gap: 36px; padding: 40px 36px 32px 36px">
  <div style="display: flex; flex-direction: column; gap: 22px; flex-grow: 1">
    <div style="display: flex; flex-direction: column; gap: 10px; max-width: 640px">
      <h1>Speedcubing from zero.</h1>
      <span class="soft" style="font-size: 16px">One unbroken ladder from your first solve
      to full CFOP, 4×4 and 5×5 — every algorithm machine-verified, every step interactive.
      Free, offline, no account.</span>
      <div style="display: flex; gap: 12px; margin-top: 6px">
        <span class="btn btn-primary">{icon("play", 15, "#fff")} Continue Phase 3</span>
        <span class="btn btn-secondary">Course overview</span>
      </div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px">
      {cards}
    </div>
  </div>
  <div style="display: flex; flex-direction: column; gap: 16px; width: 300px; flex-shrink: 0">
    <div class="card" style="padding: 18px 20px">
      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px">
        {icon("clock", 18, t["accent"])}
        <h3 style="flex-grow: 1">Today's reviews</h3>
        <span class="chip" style="background: {t["accent"]}; color: #fff">6</span>
      </div>
      {reviews}
      <span class="btn btn-primary" style="width: 100%; justify-content: center;
        margin-top: 12px; box-sizing: border-box">Start review</span>
    </div>
    <div class="card" style="padding: 18px 20px; display: flex; flex-direction: column; gap: 10px">
      <h3>Reference</h3>
      <span class="small" style="display: flex; align-items: center; gap: 8px">{icon("grid", 15, t["soft"])} <a>Notation</a></span>
      <span class="small" style="display: flex; align-items: center; gap: 8px">{icon("book", 15, t["soft"])} <a>All algorithms</a></span>
      <span class="small" style="display: flex; align-items: center; gap: 8px">{icon("download", 15, t["soft"])} <a>PDF guide &amp; cheat cards</a></span>
    </div>
  </div>
</div>
<div style="padding: 14px 36px; border-top: 1px solid {t["line"]}; display: flex; gap: 18px">
  <span class="tiny faint">Free forever · MIT + CC BY 4.0 · Open source on GitHub</span>
</div>"""


def build_lesson(t: dict) -> str:
    rows = "".join(
        case_row(t, svg, n, r, a, learned=(i < 2)) for i, (svg, n, r, a) in enumerate(OC_CASES)
    )
    return f"""
{header(t, "Learn")}
<div style="display: flex; gap: 32px; padding: 28px 36px">
  <div style="display: flex; flex-direction: column; gap: 18px; flex-grow: 1; min-width: 0">
    <div class="small" style="display: flex; gap: 8px; align-items: center">
      <a>2-Look CFOP</a> {icon("chev", 12, t["faint"])} <a>Phase 3</a>
      {icon("chev", 12, t["faint"])} <span class="soft">Orient corners</span>
    </div>
    <div style="display: flex; flex-direction: column; gap: 8px">
      <h1 style="font-size: 30px">Orient Corners: Anti-Sune + 5 New Cases</h1>
      <span class="soft">Anti-Sune completes the Sune pair. The remaining 5 cases each have
      a dedicated algorithm — every one built from triggers you already know.</span>
    </div>
    <div class="card" style="overflow: hidden">
      <div style="display: flex; align-items: center; gap: 10px; padding: 12px 18px;
          background: {t["accent_soft"]}">
        <span style="font-weight: 600; font-size: 13px; color: {t["accent"]}">ALGORITHM</span>
        <span class="tiny" style="color: {t["accent"]}">tap any case to play it in 3D</span>
      </div>
      {rows}
    </div>
    <div style="display: flex; gap: 12px; padding: 14px 18px; background: {t["warn_soft"]};
        border-left: 4px solid {t["warn"]}; border-radius: 6px">
      <div style="display: flex; flex-direction: column; gap: 2px">
        <span style="font-weight: 600; font-size: 13px; color: {t["warn"]}">CAUTION</span>
        <span class="small">Hold the cube the way the picture shows — orientation algorithms
        care about the angle. Recognition text tells you what faces you.</span>
      </div>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 4px">
      <span class="btn btn-ghost">← Sune &amp; T-Perm</span>
      <span class="btn btn-primary">{icon("check", 15, "#fff")} Mark learned · next lesson</span>
    </div>
  </div>
  <div style="width: 320px; flex-shrink: 0; display: flex; flex-direction: column; gap: 14px">
    {player_frame(t, "steps/step_7_solved.svg", ALGORITHMS["Double Headlights"], "Double Headlights — case → solved · drag to rotate")}
    <div class="card" style="padding: 14px 18px; display: flex; flex-direction: column; gap: 8px">
      <h3 style="font-size: 15px">In this phase</h3>
      <span class="small"><a>Orient corners</a> — you are here</span>
      <span class="small soft">Permute corners: Y-Perm</span>
      <span class="small soft">Permute edges: Ua + H + Z</span>
      {progress(t, 33)}
    </div>
  </div>
</div>"""


def build_case(t: dict) -> str:
    return f"""
{header(t, "Learn")}
<div style="display: flex; gap: 32px; padding: 28px 36px">
  <div style="width: 430px; flex-shrink: 0; display: flex; flex-direction: column; gap: 14px">
    {player_frame(t, "steps/step_7_solved.svg", ALGORITHMS["T-Perm"], "T-Perm — case → solved · drag to rotate")}
  </div>
  <div style="display: flex; flex-direction: column; gap: 18px; flex-grow: 1">
    <div class="small" style="display: flex; gap: 8px; align-items: center">
      <a>2-Look CFOP</a> {icon("chev", 12, t["faint"])} <a>Permute corners</a>
    </div>
    <div style="display: flex; align-items: center; gap: 16px">
      {svg_inline("pll/pll_tperm.svg", 84)}
      <div style="display: flex; flex-direction: column; gap: 4px">
        <h1 style="font-size: 30px">T-Perm</h1>
        <span class="soft">Headlights on the left — the two right corners swap, and the
        left/right edges trade places.</span>
      </div>
    </div>
    <div style="display: flex; gap: 10px">
      <span class="chip" style="border: 1px solid {t["line"]}; color: {t["soft"]}">PLL · corner swap</span>
      <span class="chip" style="border: 1px solid {t["line"]}; color: {t["soft"]}">probability 1/18</span>
      <span class="chip" style="background: {t["ok_soft"]}; color: {t["ok"]}">{icon("check", 12, t["ok"])} Learned</span>
    </div>
    <div class="card" style="padding: 16px 20px; display: flex; flex-direction: column; gap: 10px">
      <span style="font-weight: 600; font-size: 13px; color: {t["accent"]}">ALGORITHM</span>
      <div style="font-size: 17px">{alg_html(ALGORITHMS["T-Perm"], t)}</div>
      <span class="small soft">Sexy move in, <span class="tb" style="font-weight: 600">R' F</span>
      pair, then the mirror image back out. 14 moves.</span>
    </div>
    <div class="card" style="padding: 16px 20px; display: flex; flex-direction: column; gap: 8px">
      <h3 style="font-size: 15px">Practice</h3>
      <div style="display: flex; gap: 10px; align-items: center">
        <span class="btn btn-primary">{icon("target", 15, "#fff")} Drill this case</span>
        <span class="btn btn-secondary">{icon("clock", 15, t["accent"])} In review rotation</span>
      </div>
      <span class="tiny faint">Setup scramble:
        <span class="mono">{TPERM_SCRAMBLE}</span></span>
    </div>
    <div style="display: flex; gap: 8px; align-items: center">
      <span class="small soft">Pairs with</span>
      <span class="chip" style="border: 1px solid {t["line"]}">Y-Perm — the diagonal swap</span>
    </div>
  </div>
</div>"""


def build_trainer(t: dict) -> str:
    sets = ""
    for name, checked, n in [
        ("2-Look OLL", True, "10 cases"),
        ("2-Look PLL", True, "7 cases"),
        ("Full PLL", False, "21 cases"),
        ("Full OLL", False, "57 cases"),
        ("F2L", False, "41 cases"),
    ]:
        box = (
            f'<span style="display: inline-flex; width: 17px; height: 17px; border-radius: 4px; background: {t["accent"]}; color: #fff; align-items: center; justify-content: center">{icon("check", 11, "#fff")}</span>'
            if checked
            else f'<span style="display: inline-flex; width: 17px; height: 17px; border-radius: 4px; border: 1.5px solid {t["line"]}"></span>'
        )
        sets += f"""<div style="display: flex; align-items: center; gap: 10px; padding: 9px 0;
          border-top: 1px solid {t["line"]}">{box}
        <span style="font-weight: 600; font-size: 14px; flex-grow: 1">{name}</span>
        <span class="tiny faint">{n}</span></div>"""
    queue = "".join(
        f"""<div style="display: flex; align-items: center; gap: 10px; padding: 8px 0;
        border-top: 1px solid {t["line"]}">
        <span style="font-weight: 600; font-size: 14px; flex-grow: 1">{n}</span>
        <span class="chip" style="background: {bg}; color: {fg}">{lab}</span></div>"""
        for n, lab, bg, fg in [
            ("T-Perm", "again", t["warn_soft"], t["warn"]),
            ("Ua", "good", t["ok_soft"], t["ok"]),
            ("Pi", "due", t["accent_soft"], t["accent"]),
            ("Z-Perm", "due", t["accent_soft"], t["accent"]),
        ]
    )
    return f"""
{header(t, "Practice")}
<div style="display: flex; gap: 28px; padding: 28px 36px">
  <div style="width: 270px; flex-shrink: 0; display: flex; flex-direction: column; gap: 14px">
    <div class="card" style="padding: 16px 18px">
      <h3 style="font-size: 15px; margin-bottom: 6px">Case sets</h3>
      {sets}
    </div>
    <div class="card" style="padding: 16px 18px; display: flex; flex-direction: column; gap: 10px">
      <h3 style="font-size: 15px">Frequencies</h3>
      <div style="display: flex; gap: 6px">
        <span class="chip" style="background: {t["accent"]}; color: #fff">Realistic</span>
        <span class="chip" style="border: 1px solid {t["line"]}; color: {t["soft"]}">Balanced</span>
      </div>
      <span class="tiny faint">Realistic weights cases by how often they appear in solves.</span>
    </div>
  </div>
  <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 18px">
    <div class="card" style="padding: 24px; display: flex; flex-direction: column; gap: 16px;
        align-items: center">
      <span class="tiny faint" style="letter-spacing: 0.08em">SCRAMBLE · HOLD YELLOW UP</span>
      <span class="mono" style="font-size: 19px; text-align: center">{TPERM_SCRAMBLE}</span>
      <div style="display: flex; align-items: baseline; gap: 6px">
        <span class="mono" style="font-size: 64px; font-weight: 600">14.82</span>
        <span class="soft mono" style="font-size: 20px">s</span>
      </div>
      <div style="display: flex; gap: 14px">
        <span class="chip" style="border: 1px solid {t["line"]}; color: {t["soft"]}">ao5 · 18.40</span>
        <span class="chip" style="border: 1px solid {t["line"]}; color: {t["soft"]}">ao12 · 21.05</span>
        <span class="chip" style="background: {t["ok_soft"]}; color: {t["ok"]}">best · 12.96</span>
      </div>
      <div style="display: flex; gap: 12px">
        <span class="btn btn-primary">{icon("shuffle", 15, "#fff")} Next scramble</span>
        <span class="btn btn-ghost">Show case</span>
      </div>
      <span class="tiny faint">Space to start &amp; stop · works in airplane mode</span>
    </div>
    <div style="display: flex; gap: 8px; align-items: center; justify-content: center">
      <span class="tiny faint">Modes</span>
      <span class="chip" style="background: {t["accent"]}; color: #fff">Drill</span>
      <span class="chip" style="border: 1px solid {t["line"]}; color: {t["soft"]}">Recognition only</span>
      <span class="chip" style="border: 1px solid {t["line"]}; color: {t["soft"]}">Review queue</span>
    </div>
  </div>
  <div style="width: 270px; flex-shrink: 0">
    <div class="card" style="padding: 16px 18px">
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px">
        {icon("clock", 16, t["accent"])}
        <h3 style="font-size: 15px; flex-grow: 1">Review queue</h3>
        <span class="chip" style="background: {t["accent"]}; color: #fff">4</span>
      </div>
      {queue}
      <span class="tiny faint" style="display: block; margin-top: 10px">Spaced repetition
      keeps algorithms from fading — a few reviews a day.</span>
    </div>
  </div>
</div>"""


def build_mobile(t: dict) -> str:
    rows = ""
    for i, (svg, n, r, a) in enumerate(OC_CASES[:4]):
        rows += f"""
    <div style="display: flex; gap: 12px; padding: 12px 16px; border-top: 1px solid {t["line"]};
        align-items: center">
      {svg_inline(svg, 54)}
      <div style="display: flex; flex-direction: column; gap: 2px; min-width: 0; flex-grow: 1">
        <span style="font-weight: 600; font-size: 14.5px">{n}</span>
        <span class="tiny soft">{r}</span>
        <span class="wrapalg" style="font-size: 12.5px">{alg_html(a, t)}</span>
      </div>
      <span style="display: inline-flex; width: 44px; height: 44px; border-radius: 10px;
        background: {t["accent_soft"]}; color: {t["accent"]}; align-items: center;
        justify-content: center; flex-shrink: 0">{icon("play", 18, t["accent"])}</span>
    </div>"""
    tabs = "".join(
        f"""<div style="display: flex; flex-direction: column; align-items: center; gap: 3px;
        flex-grow: 1; padding: 8px 0 4px 0; color: {t["accent"] if n == "Learn" else t["faint"]}">
        {icon(ic, 21, t["accent"] if n == "Learn" else t["faint"])}
        <span class="tiny" style="font-weight: 600">{n}</span></div>"""
        for n, ic in [("Learn", "book"), ("Practice", "target"), ("Reference", "grid")]
    )
    return f"""
<div style="display: flex; align-items: center; gap: 10px; padding: 12px 16px;
    border-bottom: 1px solid {t["line"]}; background: {t["card"]}">
  {cube_mark(18)}
  <span style="font-family: 'Newsreader', Georgia, serif; font-size: 18px; font-weight: 700">cubepath</span>
  <div style="flex-grow: 1"></div>
  <span class="chip" style="background: {t["ok_soft"]}; color: {t["ok"]}">{icon("wifi-off", 12, t["ok"])} offline</span>
</div>
<div style="padding: 18px 16px 10px 16px; display: flex; flex-direction: column; gap: 6px">
  <span class="tiny" style="color: {t["accent"]}; font-weight: 600">2-LOOK CFOP · PHASE 3</span>
  <h1 style="font-size: 22px">Orient Corners</h1>
  <span class="small soft">Anti-Sune + 5 new cases, all from known triggers.</span>
  {progress(t, 33, "100%")}
</div>
<div style="background: {t["card"]}; margin: 8px 12px; border: 1px solid {t["line"]};
    border-radius: 12px; overflow: hidden">
  {rows}
</div>
<div style="position: fixed; left: 0; right: 0; bottom: 0; display: flex;
    border-top: 1px solid {t["line"]}; background: {t["card"]}">
  {tabs}
</div>"""


def build_tokens(t: dict) -> str:
    def swatch(name: str, hexv: str, border: bool = False) -> str:
        return f"""
      <div style="display: flex; flex-direction: column; gap: 6px; width: 108px">
        <div style="height: 52px; border-radius: 8px; background: {hexv};
          {f"border: 1px solid {t['line']}" if border else ""}"></div>
        <span class="tiny" style="font-weight: 600">{name}</span>
        <span class="tiny mono faint">{hexv}</span>
      </div>"""

    ui = "".join(
        swatch(*s)
        for s in [
            ("paper", T["paper"], True),
            ("card", T["card"], True),
            ("ink", T["ink"]),
            ("soft", T["soft"]),
            ("line", T["line"], True),
            ("accent", T["accent"]),
            ("ok", T["ok"]),
            ("warn", T["warn"]),
        ]
    )
    cube = "".join(
        swatch(*s)
        for s in [
            ("yellow", "#FFD500"),
            ("red", "#E00000"),
            ("green", "#009E60"),
            ("blue", "#0051BA"),
            ("orange", "#FF8C00"),
            ("grey", "#C0C0C0"),
        ]
    )
    trig = "".join(
        swatch(*s)
        for s in [("trig-r", T["trig_r"]), ("trig-g", T["trig_g"]), ("trig-b", T["trig_b"])]
    )
    callouts = ""
    for label, bg, border, text, body in [
        ("ALGORITHM", "#e8f4fd", "#2196F3", "#1565C0", "Case tables and players live here."),
        ("TIP", "#e8f5e9", "#4CAF50", "#2E7D32", "Optional speedups and shortcuts."),
        ("CAUTION", "#fff3e0", "#FF9800", "#E65100", "Mistakes that break the solve."),
        ("INFO", "#f5f5f5", "#9E9E9E", "#616161", "Background and context."),
    ]:
        callouts += f"""
      <div style="flex-grow: 1; padding: 12px 16px; background: {bg};
          border-left: 4px solid {border}; border-radius: 6px">
        <span style="font-weight: 600; font-size: 12px; color: {text}">{label}</span>
        <div class="small" style="color: {T["ink"]}">{body}</div>
      </div>"""
    return f"""
<div style="padding: 32px 36px; display: flex; flex-direction: column; gap: 26px">
  <div style="display: flex; align-items: center; gap: 12px">
    {cube_mark(24)}
    <h2>Design tokens &amp; components</h2>
    <span class="tiny faint">carried over from the PDF guide's visual language</span>
  </div>
  <div style="display: flex; flex-direction: column; gap: 10px">
    <h3>Type — Newsreader / IBM Plex Sans / IBM Plex Mono</h3>
    <h1>Orient the last layer</h1>
    <h2>Phase 3 — Complete 2-Look CFOP</h2>
    <span>Body — Hold the cube with white on bottom, yellow on top throughout.
    Nearly every algorithm reuses triggers you already know.</span>
    <span class="small soft">Small — recognition text and captions.</span>
    <div>{alg_html(ALGORITHMS["T-Perm"], T)}</div>
  </div>
  <div style="display: flex; flex-direction: column; gap: 12px">
    <h3>Color</h3>
    <div style="display: flex; gap: 14px; flex-wrap: wrap">{ui}</div>
    <div style="display: flex; gap: 14px; align-items: flex-end">{cube}
      <div style="width: 24px"></div>{trig}</div>
  </div>
  <div style="display: flex; flex-direction: column; gap: 12px">
    <h3>Buttons &amp; chips</h3>
    <div style="display: flex; gap: 12px; align-items: center">
      <span class="btn btn-primary">{icon("play", 15, "#fff")} Primary</span>
      <span class="btn btn-secondary">Secondary</span>
      <span class="btn btn-ghost">Ghost</span>
      <span class="chip" style="background: {T["ok_soft"]}; color: {T["ok"]}">{icon("check", 12, T["ok"])} Learned</span>
      <span class="chip" style="background: {T["accent_soft"]}; color: {T["accent"]}">Continue</span>
      <span class="chip" style="border: 1px solid {T["line"]}; color: {T["faint"]}">Not started</span>
    </div>
  </div>
  <div style="display: flex; flex-direction: column; gap: 12px">
    <h3>Callouts</h3>
    <div style="display: flex; gap: 12px">{callouts}</div>
  </div>
  <div style="display: flex; flex-direction: column; gap: 12px">
    <h3>Case row anatomy</h3>
    <div class="card" style="overflow: hidden; max-width: 900px">
      {case_row(T, "oll/oll_double_headlights.svg", "Double Headlights", "0 yellow — headlights left + right", ALGORITHMS["Double Headlights"], False)}
    </div>
  </div>
</div>"""


def main() -> None:
    boards = {
        "Main.dc.html": (wrap(build_main(T), T, 1280), 1280, 790),
        "Lesson.dc.html": (wrap(build_lesson(T), T, 1280), 1280, 1010),
        "Case.dc.html": (wrap(build_case(T), T, 1280), 1280, 760),
        "Trainer.dc.html": (wrap(build_trainer(T), T, 1280), 1280, 800),
        "Dark.dc.html": (wrap(build_lesson(D), D, 1280), 1280, 1010),
        "Mobile.dc.html": (wrap(build_mobile(T), T, 390), 390, 844),
        "Tokens.dc.html": (wrap(build_tokens(T), T, 1280), 1280, 1180),
    }
    for name, (html, _, _) in boards.items():
        (OUT / name).write_text(html)
    layout = {
        "artboards": [
            {"file": "Main.dc.html", "x": 0, "y": 0, "w": 1280, "h": 790},
            {"file": "Lesson.dc.html", "x": 1360, "y": 0, "w": 1280, "h": 1010},
            {"file": "Case.dc.html", "x": 2720, "y": 0, "w": 1280, "h": 760},
            {"file": "Trainer.dc.html", "x": 0, "y": 890, "w": 1280, "h": 800},
            {"file": "Dark.dc.html", "x": 1360, "y": 1110, "w": 1280, "h": 1010},
            {"file": "Mobile.dc.html", "x": 2720, "y": 860, "w": 390, "h": 844},
            {"file": "Tokens.dc.html", "x": 0, "y": 1790, "w": 1280, "h": 1180},
        ],
        "annotations": [
            {
                "id": "direction-note",
                "x": 0,
                "y": -170,
                "w": 460,
                "text": "Cubepath UI system — evolves the PDF guide's visual language: "
                "print-quality type (Newsreader + IBM Plex), the guide's callout tints, "
                "trigger-colored algorithms, and the real generated case diagrams. "
                "Light-first with a dark counterpart. All copy is real course content.",
            }
        ],
        "launch": {"view": "canvas"},
    }
    import json

    (OUT / "canvas.json").write_text(json.dumps(layout, indent=2))
    print(f"wrote {len(boards)} artboards + canvas.json to {OUT}")


if __name__ == "__main__":
    main()
