<!-- Research-backed build order for the printable card SET (not yet built).
     Produced 2026-08-26 from a 13-agent research + design + adversarial-judge
     pass. The single-card v2 (PR #1) is DONE and shipped; this document is the
     unbuilt follow-on. Keep it here rather than in a chat transcript. -->

# Cubepath Progression Set — Build Order v1.0

**Status: BUILT** (2026-08-27), on branch `cheat-card-v2`. This document is the
plan that was followed, kept for its reasoning and its numbers — not a to-do
list. Where building it disproved a claim, the claim is struck inline and the
correction is in `docs/DECISIONS.md` (§T1–§T4). Notably: the cue cap, the
"minimal clause set", the Phase 1.5 algorithm count and two of the §3 column
predictions were all wrong, and each was caught by a gate rather than by
proofreading.

---

## 1. The answer to the user's question

**Yes — make multiple cards. Make four panels: three numbered progression cards plus one un-numbered annex. Not eight. Not "Full CFOP on cards."**

| | |
|---|---|
| Card 1 / 3 | **FIRST SOLVE** — you can solve a cube at all |
| Card 2 / 3 | **TWO-LOOK** — every last layer is exactly two algorithms |
| Card 3 / 3 | **ONE-LOOK PLL** — the permute step is one algorithm |
| Card A | **ANNEX** — big cubes + the map. Not a tier, no unlock, no order |

Four panels is exactly one single-sided fold-over sheet (`_foldover` already lays out a 2×2 grid of 85.6 × 107.96 mm panels). So the answer to "one print with multiple cards" is literally one sheet, no duplexer, no flip choice, no registration error.

### Why three and not more

The rule that decides whether something is a card: **a tier exists where the learner's ability changes, and after every card the learner can still fully solve a cube.** Three moments qualify. Everything else fails one of two tests:

- **Phase 1.5 is not a card.** It exists in the guide only to *un-teach* the righty-repeat corner twist. Card 1 therefore teaches `(R' D' R D) ×2` / `(D' R' D R) ×2` **directly and never teaches the version that gets retracted**. Do not teach what you plan to retract; the rung dissolves.
- **Phase 2 is not a card.** Its content is two algorithms plus a re-ordering. Both live on Card 2 as the `START HERE` on-ramp — the thing that stops Card 2 being a 13-algorithm wall.
- **F2L is not a card.** The repo has zero F2L diagrams, `f2l-raw.json` has no recognition data (`"F2L 17"` is not a lookup key; `setup` is a generating scramble), a case needs a two-layer view the plan renderer cannot express, and the upstream source is JPerm's *best-alg reference*. A card is a memorisation aid; F2L is the one CFOP stage that is explicitly not a memorisation problem. It lives in the app (`f2l-intuition`, trainer group `full-f2l`).
- **Full OLL is not a card.** 50 new cases, ≥2 cards, and 22 of the 57 are distinguished only by side slivers. Its completion criterion cannot be stated as a solve, only as "memorised". **Stopping rule: a card stops being a progression card when its completion cannot be stated as a solve.** Full OLL is the first place that is true, so it is past the end of the set. It lives in the app trainer with randomised AUF, which beats any printed 57-case table.

Full PLL (Card 3) sits right on that line and is included for one measurable reason: it is a **closed set of 21 states you identify by sight**, its recognition cue is *derivable from the permutation* (proven below, §7.3), and it takes PLL coverage from 19/72 → 71/72 one-look. Full OLL has none of those properties at card size.

**Say this on the card, and say it in the copy:** the set stops where the medium stops. That is the honest claim, and it is printed on the annex back.

---

## 2. Fatal flaws — resolutions

| # | Flaw | Resolution | Where |
|---|---|---|---|
| F1 | Recognition cues hand-authored but stamped "machine-verified" | PLL cues are **derived from the permutation** by a new `recognition.py`. Prototype run in this repo reproduces JPerm's own group classification for all 21 (§7.3). Verification stamp is scoped to algorithms in exact wording (§6). | §7.3, §6 |
| F2 | `_SVG_SUBS` covers only `oll/` and `pll/`, so `pll-full/` would ship *worse* than today | **Delete `_SVG_SUBS` string rewriting.** Replace with a `DiagramStyle` parameter on the renderer; the card re-renders its own SVGs from the exact algorithm strings it prints. | §7.2 |
| F3 | Red vs orange unfixed; confusing them **inverts** a PLL case | New `CARD` tone palette with measured greyscale separation. Red↔orange goes **2.16:1 → 4.00:1**; every side-face pair ≥ **1.96:1** (all four pairs improve). Gate asserts it. | §7.2 |
| F4 | PLL side bands too thin to read at card size | `CARD` style widens side bands 12u → 20u. Visible fill at D=6.0 mm: 0.225 mm → **0.475 mm**. | §7.2 |
| F5 | CHUNKS never exercised on rotation-leading / parenthesised JPerm strings | `pll_algs()` normalises (strip parens, collapse space); `PLL_CHUNKS` losslessness test runs **before any layout work**. Blocking task T3. | §7.5 |
| F6 | Diagram derived from JPerm alg while card prints the repo alg | **Z-perm confirmed to differ by a y rotation.** Card re-renders every PLL diagram from the string it prints, and a test asserts state equality per row. | §7.2, §7.6 |
| F7 | Capacity costed at header+diagram pitch, prose wrap ignored | Prose costed at **0.5746 mm/char** (Typst-measured), 0.93 mm first line + 1.21 mm per extra. Every column budgeted in §3. Gate measures the real rendered column. | §3, §7.6 |
| F8 | Duplex flip-invariance dies with distinct cards | **Row-duplicated front list** `[1,1,2,2,3,3,A,A]` is invariant under σ_long (page-2 transform = nothing) and reverses under σ_short (= one whole-page rotate). Worked proof in §5. | §5 |
| F9 | Stale correctness comment at `cheatcards.py:441` | Deleted and replaced with the row-duplication theorem + three machine assertions. | §5, §7.6 |
| F10 | Calibration bar moved to sheet furniture orphans bare per-card PDFs | Every card back footer carries a **20 mm tick + "20 mm"** label. Asserted present. | §3, §5 |
| F11 | Niklas cue factually wrong | Corrected and re-derived against the simulator; test asserts the printed claim. | §6, §7.6 |
| F12 | Step numbers collide between card and guide | Card 2 and Card 3 carry **no step numbers**. Card 1 keeps the guide's 1–7. All cross-references are **by name**. | §3 |
| F13 | Glossary on a cuttable annex | Glosses print **on every card that uses the term**; the gate asserts presence *on that card*, not "defined earlier". | §6 |
| F14 | A card cannot teach a first solve | Card 1 opens with a kicker naming the `/learn` walkthrough and frames itself as the memory jog, and carries the **daisy fallback** as one line. | §3 |
| F15 | Clocks used as unlock gates | Every ADVANCE gate is a **count or a habit**. Clocks are MASTER checkboxes only, each with a blank write-in target. | §4 |
| F16 | Printed URLs create a forever contract | `/c0 /c1 /c2 /c3` frozen as tested public routes with a catch-all redirect, before printing. | §7.7 |
| F17 | Float equality in the mirror assertion | `40.540000000000006 + 202.48000000000002 + 53.98 = 297.00000000000006` — assertions use `abs(...) ≤ 0.01 mm`, never `==`. | §5 |

---

## 3. The exact card list

### Shared geometry (all four panels)

```
CARD_W, CARD_H = 85.6, 53.98      MARGIN = 2.0      usable 81.6 × 49.98
IDENT_H = 2.40   (top band, both faces)
FOOT_H  = 2.60   (bottom band, both faces)
CONTENT_H = 49.98 - 2.40 - 2.60 = 44.98        ← every column budget below
columns  = 40.2 | 1.2 mm hairline rule | 40.2  = 81.6
text slot in a row = 40.2 - D - 0.8
PUNCH: 7 × 7 mm no-print, front TOP-LEFT / back TOP-RIGHT (same physical corner
       under a book flip). Identity numeral sits at the opposite end of the band
       on each face, so it can never collide with the punch.
```

**Capacity model** (all Typst-measured in this repo, `--ignore-system-fonts`):

```
row pitch      = D + 0.27 mm
header block   = 1.85 mm
prose line 1   = 0.93 mm;  each extra line = +1.21 mm
chars per line = floor(width_mm / 0.5746)   (Libertinus 4.0pt)
alg width mm   = 1.3805·(letters+digits) + 0.5045·(primes) + 1.2612·(chunks−1)   @6.5pt
```
A wrapped algorithm costs **zero** vertical space in a diagram row: cue 0.93 + two alg lines 3.48 = 4.41 mm < any D ≥ 4.65.

---

### CARD 1 — FIRST SOLVE · 1/3 · 9 algorithms

**Algorithms (all already in `algs.py`):** Sexy Move, Lefty, Edge Insert Right, Edge Insert Left, F-sexy-F', Sune, Niklas, Orient Corners Right, Orient Corners Front. **Zero new diagrams.**

#### FRONT

*Identity band:* `1/3 · A · FIRST SOLVE` + progress `■□□`.

**Column A (40.2 mm)**

| block | content | mm |
|---|---|---|
| kicker | "New here? Do the walkthrough once at cubepath-six.vercel.app/learn. This card is the memory jog." | 2.14 |
| hdr | NOTATION | 1.85 |
| key | "R U F L D B = turn that face clockwise, looking at it from outside the cube." | 2.14 |
| key | "' = counter-clockwise. 2 = half turn. Lowercase r f = that face plus the layer behind it, turning together." | 2.14 |
| key | "y = spin the whole cube left, white staying down. A whole-cube turn solves nothing." | 2.14 |
| hdr | WORDS | 1.85 |
| gloss | "algorithm = a fixed sequence of turns. trigger = a short algorithm your hands run as one unit." | 2.14 |
| hdr | 1 · WHITE CROSS | 1.85 |
| dia | `steps/step_1_cross.svg` @ 9.0 mm | 9.00 |
| cue | "White center DOWN. Bring the four white edges to it. Each edge's side color must match the center it touches. No algorithm — work it out." | 2.14 |
| cue | "Can't see it? Build the four white edges on the YELLOW face first, each above its matching center, then turn each one down 180°." | 2.14 |
| | **total** | **29.53 / 44.98** ✓ |

**Column B (40.2 mm)** — diagrams at **D = 5.5** (white corners) and **D = 6.6** (middle edges)

| block | content | mm |
|---|---|---|
| hdr | 2 · WHITE CORNERS | 1.85 |
| cue | "Find a white corner on top, turn U until it sits above the empty slot it belongs in, then match a picture below and repeat until it drops in." | 3.35 |
| rows ×3 @5.5 | `corner_right` "white sticker faces RIGHT" → Sexy Move · `corner_front` "white sticker faces FRONT" → Lefty · `corner_up` "white sticker faces UP — run the first one once to knock it out, then look again" → Sexy Move | 17.31 |
| hdr | 3 · MIDDLE EDGES | 1.85 |
| cue | "Top edge with NO yellow: turn U until its front color matches the center under it. The arrow shows which slot it goes to." | 2.14 |
| rows ×2 @6.6 | `edge_right` → Edge Insert Right · `edge_left` → Edge Insert Left | 13.74 |
| cue | "Edge stuck in the wrong slot? Run either one to kick it out, then place it." | 2.14 |
| | **total** | **42.38 / 44.98** ✓ |

*Footer:* trigger swatch `■ R U R' U' sexy move · gap = change grip` · `20 mm ├────┤`

#### BACK

*Identity band:* `1/3 · B · FIRST SOLVE`.

**Column A**

| block | content | mm |
|---|---|---|
| hdr | 4 · YELLOW CROSS | 1.85 |
| rows ×3 @4.65 | `oll_dot` "no yellow edge at all" · `oll_hook` "two yellow edges at a right angle — hold them BACK and LEFT" · `oll_line` "hold the bar left-to-right" — all three print `F R U R' U' F'` | 14.76 |
| cue | "One algorithm, up to three times: dot → hook → line → cross. Only the yellow EDGES matter here — ignore the corners." | 2.14 |
| hdr | 5 · MATCH THE YELLOW EDGES | 1.85 |
| rows ×2 @5.5 | `align_adjacent` "two matched edges next to each other — hold them BACK and LEFT" → Sune · `align_diagonal` "two matched edges opposite" → "run it once from any hold, then look again" | 11.54 |
| cue | "First turn U so at least two top edges match the center under them. This algorithm is called Sune; you use it on every card after this one." | 3.35 |
| | **total** | **35.49 / 44.98** ✓ |

**Column B**

| block | content | mm |
|---|---|---|
| hdr | 6 · PUT THE YELLOW CORNERS HOME | 1.85 |
| rows ×2 @5.5 | `corner_cycle` "one corner already home — hold it FRONT-RIGHT" → Niklas · `corner_cycle` rot 180 "no corner home" → "run it once from any hold, then look again" | 11.54 |
| cue | **"This cycles the other three corners into place. It also twists the yellow face you just built — expected, the next step rebuilds it."** *(F11 fix)* | 2.14 |
| hdr | 7 · TWIST THE YELLOW CORNERS | 1.85 |
| rows ×2 @5.5 | `orient_right` "yellow sticker faces RIGHT" → `(R' D' R D) ×2` · `orient_front` "yellow sticker faces FRONT" → `(D' R' D R) ×2` | 11.54 |
| caution | "Between corners turn ONLY the top face, to bring the next unsolved corner to front-right. Never turn the whole cube." | 2.14 |
| caution | "The cube will look destroyed while you do this. Keep going — the last top turn brings it back." | 2.14 |
| | **total** | **33.20 / 44.98** ✓ |

*Footer, two lines:*
> LAST-LAYER ORDER ON THIS CARD: yellow cross → match edges → place corners → twist corners. **Card 2 replaces this order permanently** — it is the only thing on this card that gets retired.
> **UNLOCK CARD 2** — five scrambles in a row with this card face down. □ MASTER: those five under 3:00. My target: ______ · NEXT: 2/3 TWO-LOOK · `20 mm ├────┤`

**DONE WHEN:** five consecutive solves, card face down, nobody helping. Time is not a gate at this tier — a fast beginner method is still a beginner method.

---

### CARD 2 — TWO-LOOK · 2/3 · 13 new algorithms

**One solve step per face.** OLL on the front, PLL on the back. This is the graft that retires the shipped card's 47.4-of-48.2 mm column and buys the OLL diagrams **4.65 → 5.5 mm** for free. **Zero new diagrams.**

New: f-sexy-f', Anti-Sune, Pi, Headlights, Double Headlights, Chameleon, Bowtie, T-Perm, Y-Perm, Ua, Ub, H-Perm, Z-Perm.

#### FRONT — OLL (make the top all yellow)

*Identity band:* `2/3 · A · TWO-LOOK — OLL` + `■■□`.

**Column A**

| block | content | mm |
|---|---|---|
| hdr | OLL CROSS · yellow edges | 1.85 |
| rows ×2 @5.5 | `oll_line` "bar left-to-right" → F-sexy-F' · `oll_hook` rot 180 "hook pointing front-right" → f-sexy-f' | 11.54 |
| hdr | OLL CORNERS · yellow face | 1.85 |
| rows ×3 @5.5 | Sune "1 yellow, rest clockwise" `[1]` · Anti-Sune "1 yellow, rest counter-clockwise" `[2]` · Pi "0 yellow, headlights left" `[2]` | 17.31 |
| cue | "No yellow edge at all? Run the first one, then read again." | 0.93 |
| | **total** | **33.48 / 44.98** ✓ |

**Column B**

| block | content | mm |
|---|---|---|
| hdr | OLL CORNERS (continued) | 1.85 |
| rows ×4 @5.5 | Headlights "2 yellow, headlights at the back" `[3]` · 2× Headlights "0 yellow, headlights both sides" `[2]` · Chameleon "2 yellow next to each other" `[3]` · Bowtie "2 yellow diagonal" `[3]` | 23.08 |
| hdr | FALLBACK | 1.85 |
| cue | "The badge on each row is your fallback: that many Sunes, with a U turn between, also finishes the case. Machine-checked; three is the worst." | 3.35 |
| cue | "Top not all yellow and nothing matches? Run Sune and read again." | 0.93 |
| | **total** | **31.06 / 44.98** ✓ |

> **The `[n]` badges are derived, not claimed.** BFS over `{U, U2, U', ∅} × Sune` on the repo simulator, run for this spec:
> `Sune 1 · Anti-Sune 2 · Pi 2 · Headlights 3 · Double Headlights 2 · Chameleon 3 · Bowtie 3`. Test asserts it (§7.6). This is the Sune-counter graft, folded into the existing rows at zero diagram cost.

#### BACK — PLL (slide the top pieces home)

**Column A** — diagrams at DC = 5.5 (corners), DP = 6.6 (edges)

| block | content | mm |
|---|---|---|
| hdr | PLL CORNERS · headlights = two matching corners on one face | 1.85 |
| rows ×2 @5.5 | T "headlights on ONE face — hold that face LEFT" · Y "no headlights — the two swapping corners sit diagonally" | 11.54 |
| hdr | PLL EDGES · corners home, top still not solved | 1.85 |
| rows ×4 @6.6 | Ub "the front edge travels LEFT" · Ua "the front edge travels RIGHT" · H "both pairs swap straight across" · Z "each pair swaps with its neighbour" | 27.48 |
| | **total** | **42.72 / 44.98** ✓ (tightest column in the set — the measure gate covers it) |

**Column B**

| block | content | mm |
|---|---|---|
| hdr | START HERE — TWO NEW ALGORITHMS FINISH ANY LAST LAYER | 1.85 |
| line | "Yellow cross: F(R U R' U')F' until the cross appears — at most 3." | 0.93 |
| line | "Yellow face: Sune, read again, repeat — at most 3 (see the badges)." | 0.93 |
| line | "Corners: T-Perm. No headlights to hold left? Run it twice." | 0.93 |
| line | "Edges: Ub. No solved edge to put at the back? Run it twice." | 0.93 |
| cue | "That finishes ANY last layer with two new algorithms. Each case on the front replaces one repeat with one run. Three a week; you can solve the whole time." | 3.35 |
| hdr | H vs Z | 1.85 |
| cue | "All four side faces show a matched pair = H. Two faces matched, two not = Z. Turn U and read again before deciding." | 2.14 |
| hdr | STUCK? | 1.85 |
| cue | "Corners home but nothing solves? Turn the top face once and read again — that is often the whole fix." | 2.14 |
| cue | "One case has beaten you five times? Park it, use its fallback above, come back next week." | 2.14 |
| cue | "A single piece looks twisted and no algorithm touches it? The cube was reassembled wrong. Pop it out and reseat it." | 2.14 |
| hdr | WORDS | 1.85 |
| gloss | "OLL = make the whole top face yellow. PLL = slide the top pieces home. headlights = two matching corners on one face. AUF = the free top turn that lines a case up." | 3.35 |
| | **total** | **26.38 / 44.98** ✓ |

*Footer:*
> THE NEW ORDER: yellow cross → yellow face → corners home → edges home. **This never changes again.** Card 1's order is retired, and so is Niklas: it moves corners but wrecks the yellow face, and here the yellow face is finished first.
> **UNLOCK CARD 3** — fifteen last layers in a row, each finished in exactly two algorithms, case named out loud before your hands move. A repeat does not count. □ MASTER: solves averaging under 1:00. My target: ______ · `20 mm ├────┤`

---

### CARD 3 — ONE-LOOK PLL · 3/3 · 15 new algorithms

All 21 printed (6 already owned, marked ●) at **D = 6.0 mm**, from `pll-full/`, re-rendered in `CARD` style from the exact strings printed. Text slot 33.4 mm; two algorithms wrap (F 33.8, Na 39.3) at **zero vertical cost**.

**Learn order (ease-and-similarity, not frequency):** Ja Jb → Aa Ab → F Ra Rb → V Na Nb → E → Ga Gb Gc Gd.
**The frequency argument, settled with the repo's own numbers:** PLL probabilities sum to 71/72. Sixteen of the 21 are 4/72 each. The four G perms are 22% *as a group* but **5.6% each — identical to T and Jb** — and they are the hardest algorithms in the set. Per-case frequency cannot order this set. The card prints **coverage** instead: `Card 2 gives you 19/72 one-look. This card gives you 71/72.`

#### FRONT — ADJACENT CORNER SWAP (12 cases, exactly one face shows headlights)

**Column A:** hdr 1.85 + 6 rows × 6.27 = **39.47**, + cue "One face shows headlights: two corners of that face match. Hold as drawn, run, then turn the top to finish." 2.14 → **41.61 / 44.98** ✓
Rows: ● T · Ja · Jb · Aa · Ab · F

**Column B:** hdr 1.85 + 6 rows × 6.27 = **39.47**, + cue "Learn in the printed order, three a week, about six weeks. Ja and Jb on the same day — one is the mirror of the other." 2.14 → **41.61 / 44.98** ✓
Rows: Ra · Rb · Ga · Gb · Gc · Gd

#### BACK

**Column A — EDGES ONLY (corners already home)**
hdr 1.85 + 4 rows × 6.27 = 26.93 (● Ua ● Ub ● H ● Z) + hdr HOW TO LOOK 1.85 + three numbered lines (3.35 + 0.93 + 2.14) + "Filled dot = you already own it from Card 2." 0.93 → **34.92 / 44.98** ✓

> 1. Count the headlight faces first. One face = the front of this card. Two faces = this column. None = the column on the right.
> 2. Only then read the edges to pick the exact case.
> 3. Turn the top to line the case up as drawn, run it, turn the top again to finish. That last free turn is the AUF.

**Column B — DIAGONAL CORNER SWAP (no headlights anywhere)**
hdr 1.85 + 5 rows × 6.27 = 33.20 (● Y · V · Na · Nb · E) + hdr 1.85 + fallback 2.14 + park 0.93 + WORDS gloss (PLL / headlights / AUF) 1.36 → **41.33 / 44.98** ✓

> Case you have not learned? Two-look it from Card 2 — T-Perm then Ub still solves it. Nothing here can strand you.
> Beaten five times by one case? Park it, two-look it, come back next week.

*Footer:*
> **DONE** — all twenty-one named correctly, twenty-one in a row, no card in hand, on two separate days. □ MASTER: PLL step under 3 s, solves averaging under 0:30. My target: ______
> Next comes full OLL (57) and F2L. Both are drilled with a real cube and randomised AUF, not looked up — they live in the app: cubepath-six.vercel.app/practice · `20 mm ├────┤`

---

### CARD A — ANNEX · BIG CUBES & THE MAP · not a tier

*Identity band:* `A · ANNEX — not a tier, no unlock, no order`.

**FRONT — BIG CUBES.** Inherits the shipped card's big-cube block verbatim (already jargon-fixed to "edge pair"), with the freed space paying for the extra glosses: the reduction recipe, the big-cube notation extension (`Rw` / `3Rw` / `2R`), last-two-edges flip, 4×4 PLL parity, 4×4 OLL parity, 5×5 edge parity. All four strings continue to be read from the app script that pins them for CI.

**BACK — THE MAP.**
- THE LADDER: `1/3 FIRST SOLVE · 9 algorithms · unlock: five solves, card face down` / `2/3 TWO-LOOK · +13 · unlock: fifteen last layers in exactly two algorithms` / `3/3 ONE-LOOK PLL · +15 · done: all 21 named, twice on separate days` / `after that: full OLL, F2L, cross planning, look-ahead — in the app, not on card stock`.
- WHY THERE ARE ONLY THREE: "A card is good at a closed set of cases you tell apart by sight. It is bad at a skill you drill. F2L, cross planning and look-ahead are drills with no finite case list. Full OLL is 57 cases, 22 of which differ only in a sliver a fifth of a millimetre wide at this size. All of them are in the app, with a real cube and randomised setup. This set stops where the medium stops."
- WORDS: the full glossary (duplicating, deliberately, what the cards already gloss inline).
- PRINT & VERSION: `Every ALGORITHM on these cards is expanded from machine-verified data and checked against a cube simulator at build time; if one were wrong the build would fail rather than ship. Recognition wording is generated from the same permutation the diagram is drawn from. Set v1.0 · <build date> · reprint any single card at cubepath-six.vercel.app/print` · **Print at 100% / Actual size** · 80 mm calibration bar.

**DONE WHEN:** never. It has no unlock and no position. Use it when you buy a 4×4.

---

## 4. Progression mechanics, and how they print in greyscale

Four signals. Three of them have **zero colour dependency**.

1. **Numeral, both faces.** `1/3 · A`, `1/3 · B`, … Fixed position in the identity band, at the end opposite the punch corner. Two jobs: a card found loose is self-locating, and a manual-duplex print with the wrong flip is caught after cutting **one** card (front says 1, back says 2) instead of after wasting the sheet.
2. **Progress boxes.** `■□□`, `■■□`, `■■■` beside the numeral. Fill count and outline survive photocopying and dying toner absolutely. **Card 1 arrives with box 1 already filled**, labelled "you own a cube and you can turn it" — literally true of anyone holding it. Nunes & Drèze measured 34% vs 19% completion for pre-stamped vs equivalent-effort empty cards; this costs one filled rectangle.
3. **NEXT line + numeric unlock**, on every card back footer. A naked checkbox tracks nothing; the criterion is the product.
4. **Tier tint** — bonus channel only. Identity band rule tinted on a descending lightness ramp L\* ≈ 78 / 62 / 46 (annex: 88). In greyscale it degrades to an ordinal light-to-dark staircase, never to mush. Deliberately **not** the vivid equal-weight trigger hues (`#A61B1B` / `#1B5E20` / `#12408C`), so the two colour systems cannot be read as one code.

**Gates: counts advance, clocks are optional.** Every ADVANCE criterion is a count or a habit — at these tiers a clock measures the method, not the solver, and a printed number a casual learner never reaches means they never unlock the rest of what they printed. Every MASTER line is a checkbox with a **blank write-in target** beside it.

**Park rule (Anki's leech suspend, without a scheduler).** Printed on Cards 2 and 3: *"beaten five times by one case? Park it, use the fallback, come back next week."* The fallback is on the same card, so parking never costs the ability to finish a solve.

**Supersession — exactly one, printed on both sides of the seam,** generated from the deck table and cross-checked by a test: Card 1 footer → "Card 2 replaces this order permanently"; Card 2 footer → "Card 1's order is retired. So is Niklas."

**Cards are reordered, never discarded.** A finished card goes to the back of the stack: Card 1 is the highest-value thing in the set to hand to a friend, and STUCK? is exactly what you need after a six-month layoff.

---

## 5. Print plan

### 5.1 Default: fold-over, one single-sided sheet, no duplexer

`_foldover` already places `rotate(180deg, card-back)` directly above `card-front` sharing a fold edge, 2×2 panels of 85.6 × 107.96 mm. The **only** change is a per-cell card index. Panels in reading order: **1, 2 / 3, A**.

```
block 171.2 × 215.92
A4     x0 = (210   − 171.2)/2 = 19.40   y0 = (297   − 215.92)/2 = 40.54
Letter x0 = (215.9 − 171.2)/2 = 22.35   y0 = (279.4 − 215.92)/2 = 31.74
```
No mirror, no permutation, no flip mode, no registration error, works on printers with no duplexer. Folding 160–200 gsm gives ~0.32–0.40 mm, closer to real ID-1 (0.76 mm) than a single 250 gsm sheet at 0.25 mm.

Sheet furniture (printed once, in the top margin): 80 mm calibration bar · "Print at 100% / Actual size, **SINGLE-sided**" · "**Crease** along the grey line, fold so both printed faces are outward, glue, then cut."

### 5.2 Opt-in: duplex, 2×4, two complete sets per sheet

Slots numbered `s = 2r + c`, 0-based, reading order.

```
A4      X = [19.400, 105.000]   Y = [ 40.540,  94.520, 148.500, 202.480]
Letter  X = [22.350, 107.950]   Y = [ 31.740,  85.720, 139.700, 193.680]
```

Mirror identities (**assert with `abs(...) ≤ 0.01`, never `==`** — F17):

```
19.400 + 105.000 + 85.6 = 210.000 ✓     22.350 + 107.950 + 85.6 = 215.900 ✓
40.540 + 202.480 + 53.98 = 297.000 ✓    31.740 + 193.680 + 53.98 = 279.400 ✓
94.520 + 148.500 + 53.98 = 297.000 ✓    85.720 + 139.700 + 53.98 = 279.400 ✓
```

**Permutations** (back-sheet slot `s` lands behind front slot `σ[s]`):

```
σ_long  = [1, 0, 3, 2, 5, 4, 7, 6]      # (r,c) → (r, 1−c);  content upright
σ_short = [6, 7, 4, 5, 2, 3, 0, 1]      # (r,c) → (3−r, c);  + whole-page 180°
ρ[s]    = 7 − s                          # whole-page 180° rotation
σ_short = ρ ∘ σ_long                     # 0→1→6 ✓  1→0→7 ✓  2→3→4 ✓  3→2→5 ✓
```

**The front list is row-duplicated:**

```
F = [1, 1, 2, 2, 3, 3, A, A]
```

Back page content is `B[s] = F[σ[s]]`.

- **Long edge:** `B[s] = F[s XOR 1] = F` because `F[2k] == F[2k+1]`. **The page-2 transform is literally nothing** — the flip-agnostic property the repo engineered for identical cards, recovered for a distinct-card deck.
- **Short edge:** `B = F[σ_short] = [A,A,3,3,2,2,1,1] = reverse(F)`. Emitting the *same* list `F` and wrapping page 2 in `rotate(180deg, origin: center + horizon, block(210mm, 297mm)[…])` places the card laid at slot `k` physically at `ρ[k] = 7−k`, so physical slot `s` receives `F[7−s] = reverse(F)[s]` — exactly `B`. ✓

**Theorem to assert, not assume:** row-duplication (`F[2k] == F[2k+1]`) is what makes both permutations act as identity/reverse on the card list. A future reorder that interleaves cards silently scrambles every duplex print with no visible symptom on a proof sheet.

**The trap:** a naive whole-page 180° rotation *alone* maps `(r,c) → (r, 1−c)` — it degenerates into the long-edge column swap and pairs Card 1's front with Card 2's back. Invisible on today's symmetric all-identical sheet.

**Files:** `deck-{a4,letter}-fold.pdf` (default) · `deck-{a4,letter}-duplex-long.pdf` · `deck-{a4,letter}-duplex-short.pdf`. **Never one duplex file claiming to work under either flip.** Strip text on duplex sheets names the flip explicitly and says "the numeral on both faces is your check: cut one card first."

### 5.3 Per-card outputs

- `card-{0,1,2,3}-{slug}.pdf` — 2 pages, bare ID-1, page 1 front / page 2 back. What a PVC card service wants.
- `card-N-{slug}-fold-{a4,letter}.pdf` — one sheet, four copies of that one card. Wallet, desk, bag, and the one you will lose. **This preserves today's best property** (one print gives you several copies of the card you actually want) and is what `print.astro` defaults to.
- `manifest.json` at `guide/build/cards/manifest.json` (copied to `app/src/data/cards.json`, which is what the app imports) — `{cards, sheets}`: the ordered card table driving the app ladder, the NEXT footers and the supersession text, plus every whole-deck sheet the build writes, so `print.astro` never re-types a filename. `tests/test_cards.py` pins the committed copy to the generator, because CI does not run `cubepath-cards`.

Zero gutter stays zero gutter: a ±1 mm cut drift takes a sliver of the neighbour, and that sliver is white only because the neighbour's outer 2 mm is blank margin. **That 2 mm margin is load-bearing as cut tolerance and can never be spent on content.**

---

## 6. Jargon fixes — exact before → after

All in `tools/diagrams/src/cubepath/cheatcards.py` unless noted. Every replacement was measured against its real column; none wraps.

| line | before | after |
|---|---|---|
| 149 | `1 yellow, rest CW` | `1 yellow, rest clockwise` |
| 150 | `1 yellow, rest CCW` | `1 yellow, rest counter-clockwise` |
| 151 | `0 yellow, lights left` | `0 yellow, headlights left` |
| 152 | `2 yellow, lights back` | `2 yellow, headlights at the back` |
| 153 | `0 yellow, lights L+R` | `0 yellow, headlights both sides` |
| 169 | `righty / lefty -- corner above its slot…` | `sexy move / lefty -- corner above its slot…` |
| 176 | `swaps a corner+edge pair, leaves the yellow face alone` | `cycles 3 corners; it twists the yellow face — the next step rebuilds it` |
| 231 | `Corners not oriented?` | `Top not all yellow?` |
| 259 | `gap = new grip` | `gap = change grip` |
| 243 | `sledge` | `sledgehammer` |
| 302 | `= anti-clockwise` | `= counter-clockwise` |
| 305 | `2R = *INNER SLICE ONLY* -- never widen it` | `2R = *2nd LAYER ONLY* -- never widen it` |
| 313 | `use it until you know steps 5--6` | `use it until you know Sune` |
| 319 | `build 6 centres → pair the 12 edges` | `build the 6 centers → pair the 12 edges` |
| 326 | `2 edge pairs swapped · 50%` | `2 edge pairs swapped · half the time` |
| 329 | `1 edge pair flipped · 50%` | `1 edge pair flipped · half the time` |
| 331 | `1 edge pair flipped · 50% · one token differs` | `1 edge pair flipped · half the time · one move differs` |
| 334 | `both parity algs move corners` | `both parity algorithms move corners` |
| 340 | `the no-duplex fold-over version` | `the one-sided fold-over version` |
| 553 | `Score the grey line` | `Crease along the grey line` |
| all | `colour(s)`, `centre(s)` | `color(s)`, `center(s)` |
| `app/src/content/lessons/444-yau-intro.mdx` ×7 | `dedge` | `edge pair` — **plus one parenthetical at first use**: `edge pair (cubers write "dedge")` |

**Verification stamp, exact wording** (annex back — F1):
> Every **algorithm** on these cards is expanded from machine-verified data and checked against a cube simulator at build time; if one were wrong the build would fail rather than ship. Recognition wording is **generated from the same permutation the diagram is drawn from**.

### The vocabulary rule (three tiers)

- **TEACH** — gloss in ≤ 6 words, **on every card that uses the term**: OLL, PLL, Sune, sexy move, sledgehammer, headlights, trigger, AUF, parity, edge pair, F2L, look-ahead, adjacent/diagonal corner swap.
- **BAN** — with its replacement: `dedge → edge pair` · `alg/algs → algorithm` · `token → move` · `lights → headlights` · `regrip → change grip` · `OCLL, EO, CO, EP, CP, 2GLL, n-mover → deleted` · `50% → half the time` · `inner slice → 2nd layer only` · `score (verb) → crease` · `duplex → two-sided` (on cards; the word may live in build filenames).
- **ALWAYS PLAIN** — never introduce the term: `permute → slide the pieces home` · `orient → make the top all yellow` · `reduction → the three-arrow recipe already printed`.

**Enforcement is definition-on-*this*-card, not definition-earlier-in-order** (F13). A term defined once on Card 1 is forgotten by Card 3, and the annex is cuttable. Deliberate redundancy is the design, not a defect.

---

## 7. Implementation plan against this repo

### 7.1 New / changed files

```
tools/diagrams/src/cubepath/
  cards.py        NEW  deck table + per-card Typst builders (replaces the card
                       content half of cheatcards.py)
  recognition.py  NEW  derived PLL cues + derived Sune fallback counts
  glossary.py     NEW  GLOSS / BANNED tables
  cheatcards.py   REWRITE  imposition, gates, CLI  (entry point → cubepath-cards)
  fullsets.py     EDIT  pll_algs(), card-styled render entry
  diagrams.py     EDIT  DiagramStyle parameter (SCREEN | CARD)
  notation.py     EDIT  PLL_CHUNKS for the 15 new algorithms
tools/diagrams/tests/
  test_cards.py   NEW   deck, imposition, capacity, glossary, palette gates
  test_recognition.py NEW derived cues + Sune counts
app/
  src/pages/c/[n].astro  NEW frozen routes /c0 /c1 /c2 /c3
  src/pages/print.astro  EDIT  per-card default, new filenames
  src/data/algs.ts       EDIT  optional `card?: "c1"|"c2"|"c3"` on CaseDef
  src/content/lessons/444-yau-intro.mdx  EDIT  dedge → edge pair
guide/cubepath.md  EDIT  Phase 1.5 "+0" → "+3"; What's Next: Full PLL before Full OLL
Makefile           EDIT  `cards` target (keep `cheatcards` as a deprecated alias)
docs/DECISIONS.md  EDIT  log: 3-card set; American spelling; card routes frozen
```

### 7.2 Diagram styling — replaces `_SVG_SUBS` entirely (F2, F3, F4, F6)

```python
@dataclass(frozen=True)
class DiagramStyle:
    faces: dict[str, str]      # face letter -> hex
    band_u: int                # side-band thickness in viewBox units
    stroke_main: float
    stroke_side: float

SCREEN = DiagramStyle(faces=SCREEN_FACES, band_u=12, stroke_main=1.5, stroke_side=1.0)
CARD   = DiagramStyle(faces=CARD_FACES,   band_u=20, stroke_main=3.2, stroke_side=2.4)
```

**`CARD_FACES` — measured greyscale-separated palette:**

| face | screen | card | rel. luminance |
|---|---|---|---|
| F red | `#E00000` | **`#A30A0A`** | 0.0803 |
| B orange | `#FF8C00` | **`#FFA13C`** | 0.4708 |
| R green | `#009E60` | **`#0A9048`** | 0.2048 |
| L blue | `#0051BA` | **`#001A5C`** | 0.0151 |
| U yellow | `#FFD500` | `#FFD500` | 0.6885 |
| masked | `#C0C0C0` | `#5F5F5F` | — |

Greyscale contrast ratios, current → card:

```
red↔orange  2.16 → 4.00      red↔green  1.45 → 1.96
red↔blue    1.44 → 2.00      orange↔green 1.49 → 2.04
orange↔blue 3.12 → 8.00      green↔blue 2.10 → 3.91
```
Every pair improves; the inverting pair (red↔orange, opposite faces) improves 1.85×.

**Band widening** (`band_u = 20`) is a coordinate rewrite that grows the band outward, inner edge fixed:
`y=20,h=12 → y=12,h=20` (top) · `y=160,h=12 → y=160,h=20` (bottom) · `x=20,w=12 → x=12,w=20` (left) · `x=160,w=12 → x=160,w=20` (right). Visible fill = `D·(band_u − 4.8)/192`; at D = 6.0 mm this is **0.475 mm** vs 0.225 mm today.

**Card diagrams are re-rendered, not rewritten.** `cards.py` calls the generator with `style=CARD` and the **exact algorithm string the card prints**, so diagram, cue and algorithm can never disagree. This is what closes F6 — verified in this repo: **the repo's Z-Perm and JPerm's Z-Perm solve states differing by a `y` rotation**, so the shipped `pll_full_z.svg` does not match the string Card 3 prints for Z.

### 7.3 `recognition.py` — derived PLL cues (F1)

Prototyped and run in this repo. For each case, `state_before(printed_alg)` and read the U-layer row of each side face `F, R, B, L`:

```
BAR    s[0]==s[1]==s[2]      (that face is solved)
lights s[0]==s[2]            (headlights)
blkL   s[0]==s[1] != s[2]
blkR   s[1]==s[2] != s[0]
```

**Result — the derivation reproduces JPerm's own group classification for all 21:**

| headlight faces | derived group | JPerm `group` |
|---|---|---|
| 4 | corners already home | Edges Only ✓ |
| 1 | adjacent corner swap | Adjacent Corner Swap ✓ |
| 0 | diagonal corner swap | Diagonal Corner Swap ✓ |

Full derived fact table (abridged): `T` lights L + blkL F + blkR B · `Ja` BAR L + blkL everywhere · `Jb` BAR L + blkR everywhere · `F` BAR L only · `Aa` lights L + blkR F + blkL R · `Ab` lights L + blkR R + blkL B · `Ra` lights L + blkL F · `Rb` lights L + blkR B · `Ga` lights L + blkR F · `Gb` lights L + blkR R · `Gc` lights L + blkL B · `Gd` lights L + blkL R · `Y` blkL F + blkR R · `V` blkL F + blkR L · `Na` blkR ×4 · `Nb` blkL ×4 · `E` nothing.

**All 21 are separated by the corner clause except two pairs** — `{Ua, Ub}`
and `{H, Z}` — which require the edge clause (cycle direction / opposite-vs-adjacent
swap), derived from the same U-layer permutation the arrows already come from and
are already permutation-verified against.

> **BUILT — and three claims above are wrong. See `docs/DECISIONS.md` §T3.**
> The load-bearing claim holds: the derivation reproduces JPerm's group for all
> 21, and the two collisions are exactly the two predicted. But:
> 1. There is **no minimal positive clause set** for ten of the 21 — recognition
>    is closed-world. `Ga` is exactly `L headlights + F pair`, and `Aa` is that
>    *plus* one more, so no subset of Ga's facts excludes Aa. Cues state the
>    whole signature.
> 2. `CUE_MAX_CHARS` is **51, not 34** — measured. The widest real cue (Ua, 48
>    chars) is 26.97 mm, 81% of the 33.4 mm slot.
> 3. The fact table above differs from the derivation by a systematic flip on
>    the R and B faces — a strip reading-direction convention. Do not hand-copy
>    it; `recognition.py` derives it, and a geometric test pins the direction
>    against the renderer.
>
> Also tested and **false**: "a matching pair means that corner is home" (14 of
> 30 pairs violate it). It was never printed, because it was checked first.

**Derived Sune fallback counts** for Card 2: BFS over `{∅, U, U2, U'} × Sune` from `state_before(case_alg)` to `u_face_solved()`. Run for this spec: `{Sune:1, Anti-Sune:2, Pi:2, Headlights:3, Double Headlights:2, Chameleon:3, Bowtie:3}` — max 3, which is what licenses "at most three Sunes" in print.

### 7.4 Data model

```python
@dataclass(frozen=True)
class Card:
    num: int | None          # None => annex
    slug: str                # "first-solve" | "two-look" | "one-look-pll" | "annex"
    title: str
    tint_L: int              # 78 / 62 / 46 / 88
    unlock: str              # ADVANCE criterion, printed verbatim
    master: str              # MASTER checkbox text
    next_slug: str | None
    supersedes: str | None   # slug whose block this retires
    superseded_by: str | None
    front: Callable[[], str] # Typst
    back:  Callable[[], str]

DECK: list[Card]                     # ordered; index == fold panel index
FRONT_SLOTS = [0,0,1,1,2,2,3,3]      # duplex: row-duplicated card indices
```

Card 3's rows come from `cards.pll_deck() -> list[PllRow]` where each row carries `(name, alg, source, owned: bool)`; `source == "algs.py"` for the six owned cases and `"jperm-raw"` for the fifteen new. Nothing is retyped, and the owned six print the string the learner already knows.

### 7.5 Blocking task order

1. **T1** `PLL_CHUNKS` + normalisation. `pll_algs()` strips parentheses (`T`, `Nb`, `Ga`–`Gd`) and collapses whitespace; handles leading rotations (`x` in `Aa`, `Ja`; `x'` in `Ab`, `E`) and the mid-algorithm `y` in `V`. `expand(PLL_CHUNKS[k]) == pll_algs()[k]` character for character, all 21. **Do this before any layout work** — chunk count changes measured algorithm width, and every column number in §3 depends on it.
2. **T2** `DiagramStyle` + `CARD_FACES` + `band_u=20`; delete `_SVG_SUBS`; palette contrast gate.
3. **T3** `recognition.py` + its tests.
4. **T4** `cards.py` deck + Cards 1 and 2 (zero new diagrams — buildable today).
5. **T5** Card 3 + annex.
6. **T6** Imposition rewrite + assertions + per-card outputs + manifest.
7. **T7** App: frozen `/c0`–`/c3` routes, `print.astro`, `manifest.json` consumption, `dedge` fix.
8. **T8** Guide corrections + `docs/DECISIONS.md`.

### 7.6 Tests that guard it

**`test_cards.py`**

| test | asserts |
|---|---|
| `test_each_card_is_two_id1_pages` | per card: `Pages == 2`, page size == ID-1 ±0.1 pt. Typst paginates silently on overflow |
| `test_no_column_overflows` | Typst `measure()` of every rendered column ≤ 44.98 mm. **The gate that replaces hand arithmetic** (F7) |
| `test_mirror_invariance` | `abs(X[c] + X[1−c] + CARD_W − PAGE_W) ≤ 0.01` and `abs(Y[r] + Y[3−r] + CARD_H − PAGE_H) ≤ 0.01`, both sheets. **Never `==`** (F17) |
| `test_permutations_are_involutions` | `σ[σ[i]] == i` for both tables; `σ_short == [ρ[σ_long[i]] for i]` |
| `test_front_list_is_row_duplicated` | `F[2k] == F[2k+1]` — the theorem the whole duplex scheme rests on |
| `test_blank_slots_travel_under_sigma` | blank set on page 2 == σ(blank set on page 1). Dormant at N=8, live the moment a card is cut |
| `test_short_edge_page_two_is_rotated` | short-edge file contains the rotate wrapper; long-edge file does not |
| `test_face_palette_contrast` | every side-face pair in `CARD_FACES` ≥ 1.95:1 greyscale contrast |
| `test_side_bands_are_widened` | exactly 12 band rects per card PLL SVG, all at `band_u = 20` |
| `test_calibration_tick_on_every_back` | `"20 mm"` present in every card's page-2 text (F10) |
| `test_no_banned_terms` | `pdftotext` of each card contains no `BANNED` term |
| `test_teach_terms_glossed_on_their_own_card` | for each `TEACH` term in a card's text, that card's text also contains its gloss (F13) |
| `test_supersession_is_symmetric` | every `supersedes` has a matching `superseded_by` and both strings render |
| `test_no_step_numbers_on_cards_2_and_3` | regex for `step \d` / leading numerals in headers (F12) |
| `test_smart_quotes` / `test_markup_leak` / `test_every_algorithm_appears` | retained from `test_cheatcard.py`, extended to all four cards |

**`test_recognition.py`**

| test | asserts |
|---|---|
| `test_derived_group_matches_jperm` | headlight-face count → group == `jperm-raw` group, all 21 |
| `test_cues_are_unique` | all 21 generated cues pairwise distinct |
| `test_cue_length` | every cue ≤ `CUE_MAX_CHARS` |
| `test_printed_alg_solves_printed_diagram` | for every Card 3 row, `state_before(printed_alg)` == the state the printed diagram was rendered from (**F6 / the Z-perm bug**) |
| `test_sune_counts` | BFS reproduces `{1,2,2,3,2,3,3}` and max == 3 |
| `test_niklas_cue_is_true` | `not u_face_solved()` after Niklas from a solved cube, i.e. the printed "it twists the yellow face" is the simulator's answer (F11) |

**Playwright (app):** `/c0`, `/c1`, `/c2`, `/c3` return 200 and land on the right trainer group; a catch-all `/c*` redirects rather than 404s. Treated as **frozen public API** — a printed card cannot be redeployed (F16).

### 7.7 App contract

`CaseDef` gains an optional `card?: "c1" | "c2" | "c3"`, populated by `gen-cases.mjs` from `manifest.json`, so "you have finished this card" is **computed from the trainer**, not claimed on paper. `/cN` renders the ladder position, the unlock criterion, the matching trainer group, and a link to `card-N-{slug}-fold-a4.pdf`.

---

## 8. Prior art

**Nothing comparable exists.** Every cubing card product on the market is organised by **algorithm set** or by **case**. None contains the beginner method. None is used in order.

| product | what it is |
|---|---|
| **Z-Cube CFOP Cards** (this repo's original inspiration) | 3 plastic cards, 86 × 55 mm, ~€5 / $0.99 — one card each for F2L, OLL, PLL. Pure reference: *"if you forget an algorithm you always have the cards with you."* No beginner content, no ordering, no completion gate. Documented complaints: text "too small", "cannot tell R from R′ even with a magnifying glass", "the PLL cards do not include the name… you have to guess from the color and arrows", "red and orange look almost the same", and one PLL diagram printed at the wrong rotation |
| **SpeedCubeShop CFOP Algorithm Flashcards** | 120 cards, one case per card, $20.95, QR per card. Ships a recommended order (PLL → OLL → F2L) but only *within* CFOP. Reviews: "algs are kinda outdated in 2025", inconsistent card sizing across sets. Bundles the **notation card inside the PLL set** — the prerequisite arrives with the last material bought |
| **Drift OLL/PLL cards** (Cubelelo) | 78 poker-sized cards, last layer only, no progression |
| **Etsy CFOP last-layer deck** | 78 print-at-home cards, nicknames + multiple angles, no progression |
| **`d-grasshopper/speed-cube-flash-cards`** | MIT, hand-drawn in Illustrator from JPerm PNGs via png2svg. No generator, no verification, no progression |
| **Rubik's Coach Cube** | the only *gated* product in cubing — peel-to-reveal stickers, 8 steps, QR per step. It is a cube, not cards, and it stops at the beginner method |
| **Anki OLL/PLL decks** | exist; the community's own verdict is that SR trains recall when the skill is muscle memory, and reverse-scramble cards teach you to memorise the *scramble*. **We deliberately ship none** |

### Where this set beats all of it

1. **Organised by learner stage, not by algorithm set.** The empty slot. Nobody cards the first solve; nobody numbers or gates their cards.
2. **Every card leaves you able to solve a cube**, and Cards 2 and 3 print their fallback to the previous card. No incumbent can say this because none of them starts below CFOP.
3. **Card order is reading order**, which makes "define every term where it is used" *mechanically enforceable* — and it is enforced in `make check`, not by proofreading. This is precisely the defect class that produced the "dedge" finding, and precisely what the category systematically gets wrong.
4. **Nothing is retyped and the recognition wording is derived**, not written — the cue generator reproduces JPerm's own case classification independently. No competitor states a data source, a verification method, or a revision date anywhere on the product; two of them draw "algorithms are outdated / don't work" reviews.
5. **Every Z-Cube legibility complaint is answered with a number.** R vs R′: the boxed prime pulled 0.20 em left (already shipping). Missing case names: printed. Text too small: measured column gates. Red vs orange: **2.16:1 → 4.00:1**, with a build gate. Wrong-rotation diagram: impossible, because each diagram is re-rendered from the string printed beside it and a test asserts the two agree.
6. **The QR/short link points at a live kpuzzle-verified trainer with randomised AUF**, not a static list or a video. No vendor in this category owns a trainer.
7. **One sheet, no duplexer, and the duplex variants are flip-agnostic anyway** via the row-duplication theorem — while still giving two complete sets per sheet.
8. **It admits where paper stops.** Full OLL and F2L are named on the card as app work, with the reason printed. That is the one claim no reference deck can make, and it is why this set is three cards instead of eight.