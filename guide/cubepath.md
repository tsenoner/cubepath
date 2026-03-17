---
title: "Cubepath"
subtitle: "From Beginner to 2-Look CFOP"
author: "Based on Cube.Academy methods"
date: 2026-03-17
---

# Introduction

Most tutorials teach the beginner method, then expect you to jump to CFOP. The problem: the two methods use **different last-layer orders**, and beginner algorithms break when you switch.

**Beginner:** Yellow Cross → Align Edges → Position Corners → Orient Corners\
**CFOP:** Yellow Cross → Orient Corners → Position Corners → Align Edges

This guide bridges the gap in 3 phases:

1. **Phase 1** — Beginner method. Solve the cube reliably.
2. **Phase 2** — Switch to CFOP order with 5 new algorithms.
3. **Phase 3** — Complete 2-Look CFOP with 6 more algorithms.

**Key idea:** nearly every new algorithm reuses triggers you already know — the sexy move, Sune, and F-sexy-F'.

Hold the cube with **white on bottom, yellow on top** throughout.


# Notation

Each letter = 90° clockwise (looking at that face). Apostrophe (') = counterclockwise. "2" = 180°.

| Move | Meaning |
|------|---------|
| `R` / `R'` / `R2` | Right face CW / CCW / 180° |
| `U` / `U'` / `U2` | Up face CW / CCW / 180° |
| `L` / `L'` | Left face CW / CCW |
| `F` / `F'` | Front face CW / CCW |
| `D` / `D'` | Down face CW / CCW |
| `f` / `r` (lowercase) | Wide move — two layers together |
| `M` / `M2` | Middle layer (same direction as L) / 180° |
| `x` / `y` / `z` | Whole-cube rotation (R / U / F direction) |

::: algorithm
**The Sexy Move: `R U R' U'`** — The most important trigger in cubing. Practice until it's muscle memory.
:::


# Phase 1: Beginner Method

## White Cross (Intuitive)

Build a white cross on the bottom, matching each edge's side color to its center. No algorithms — plan ahead, then execute.

## White Corners

Position a white corner above its correct slot, then:

| White sticker faces | Algorithm |
|---------------------|-----------|
| Right | `R U R' U'` (1× Righty) |
| Front | `(R U R' U')` ×3 |
| Up | `(R U R' U')` ×5 |
| Left | `L' U' L U` (1× Lefty) |

::: tip
Corner stuck in bottom? One Righty pops it out.
:::

## Middle-Layer Edges

Find a top-layer edge without yellow. Turn U until its front color matches the center below.

| Edge goes | Algorithm |
|-----------|-----------|
| Right | `U (R U R' U') y' (L' U' L U)` |
| Left | `U' (L' U' L U) y (R U R' U')` |

Wrong slot? Insert any top-layer edge to push it out.

## Yellow Cross

Flip the cube — yellow on top. One algorithm handles all cases:

::: algorithm
**F-sexy-F': `F (R U R' U') F'`** — just the Sexy Move wrapped with F and F'.
:::

![Dot](figures/generated/oll_dot.svg){ width=15% }
![Hook](figures/generated/oll_hook.svg){ width=15% }
![Line](figures/generated/oll_line.svg){ width=15% }

| You see | Action |
|---------|--------|
| Dot | Apply twice: Dot → Hook → Cross |
| Hook | Hold L in **back-left**, apply once |
| Line | Hold line **horizontal**, apply once |

## Align Yellow Edges

Turn U to match as many edges as possible to their centers.

::: algorithm
**Sune + U: `R U R' U R U2 R' U`** — cycles 3 edges.
:::

- **Two adjacent correct:** Hold them at back + right, apply once.
- **Two opposite correct:** Apply from any angle → gives adjacent, then repeat.
- **None correct:** Apply once, realign, repeat.

## Position Yellow Corners

Find a corner in its correct position (colors match neighboring centers — twist doesn't matter). Hold it at **front-right-top**.

::: algorithm
**Niklas: `R U' L' U R' U' L`** — cycles the other 3 corners. Repeat if needed.
:::

No correct corner? Apply from any angle — one will land correctly.

::: info
Niklas disrupts orientation — that's OK here. We haven't oriented corners yet, so it doesn't matter. This is exactly why the beginner order works: permute *then* orient.
:::

## Orient Yellow Corners

1. Hold an unsolved corner at front-right-top.
2. Repeat `(R U R' U')` until its yellow faces up (2 or 4 reps).
3. Turn **only U** to bring the next unsolved corner to front-right-top.
4. Repeat until done. One final U turn may be needed.

::: caution
The cube looks scrambled mid-step. Trust the process: only turn U between corners, never rotate the cube or turn other layers. Everything falls into place once all four corners are oriented.
:::

## Phase 1 Summary

| Algorithm | Name | Used for |
|-----------|------|----------|
| `R U R' U'` | Sexy Move | Everywhere |
| `L' U' L U` | Lefty | White corners (mirror) |
| `F (R U R' U') F'` | F-sexy-F' | Yellow cross |
| `R U R' U R U2 R'` | Sune | Edge alignment (+U) |
| `R U' L' U R' U' L` | Niklas | Corner positioning |
| Repeat `(R U R' U')` | — | Corner orientation |


# Phase 2: CFOP Switch (+5 Algorithms)

Switch to CFOP order. This eliminates the two slowest beginner steps:

- **Repeated sexy** for corner orient (~48 moves) → **Sune/Anti-Sune** (~12 moves)
- **Niklas** for corner position → **T-perm/Y-perm** (preserves yellow face)
- **Sune+U** for edge alignment → **Ua/Ub** (dedicated edge perms)

::: info
**New last-layer order:** OE (Cross) → **OC** (Orient Corners) → **PC** (Position Corners) → **PE** (Align Edges). All orientation first, then all permutation. This never changes again.
:::

## Yellow Cross (Updated)

The Line case gets its own efficient algorithm using wide `f`:

![Dot](figures/generated/oll_dot.svg){ width=15% }
![Hook](figures/generated/oll_hook.svg){ width=15% }
![Line](figures/generated/oll_line.svg){ width=15% }

| You see | Algorithm |
|---------|-----------|
| Dot | `F (R U R' U') F'` then `f (R U R' U') f'` |
| Hook | `F (R U R' U') F'` — hold L in back-left |
| Line | `f (R U R' U') f'` — wide `f`, hold horizontal |

## Orient Corners: Sune + Anti-Sune

After the cross, look at the four corners. Use Sune to reduce any case to Sune or Anti-Sune:

![Sune](figures/generated/oll_sune.svg){ width=15% }
![Anti-Sune](figures/generated/oll_antisune.svg){ width=15% }

::: algorithm
| Case | Algorithm |
|------|-----------|
| Sune (1 yellow corner, others CW) | `R U R' U R U2 R'` |
| Anti-Sune (1 yellow corner, others CCW) | `R U2 R' U' R U' R'` |
:::

::: tip
**Start with just Anti-Sune.** For unknown cases, apply Sune until you get a case you recognize. The remaining 5 corner cases are covered in Phase 3.
:::

## Permute Corners: T-Perm + Y-Perm

Yellow face complete. Check side colors for **headlights** (two matching corners on one face).

![T-Perm](figures/generated/pll_tperm.svg){ width=15% }
![Y-Perm](figures/generated/pll_yperm.svg){ width=15% }

::: algorithm
| Case | Algorithm |
|------|-----------|
| Headlights on one face | `R U R' U' R' F R2 U' R' U' R U R' F'` (T-Perm) — hold headlights at **back** |
| No headlights | `F R U' R' U' R U R' F' R U R' U' R' F R F'` (Y-Perm) — any angle |
| All corners match | Skip |
:::

::: caution
Niklas can't be used here — it destroys the yellow face you just built. T/Y-Perm swap corners while preserving it.
:::

## Permute Edges: Ua + Ub

Corners done. Turn U — find the solved edge, hold it at **back**.

![Ua Perm](figures/generated/pll_ua.svg){ width=15% }
![Ub Perm](figures/generated/pll_ub.svg){ width=15% }

::: algorithm
| Case | Algorithm |
|------|-----------|
| Front edge → right | `M2 U M U2 M' U M2` (Ua) |
| Front edge → left | `M2 U' M U2 M' U' M2` (Ub) |
| No single edge solved | Do Ua → creates a U-perm → do the other |
:::

::: tip
**M-slice moves** are the first genuinely new finger trick. `M` turns the middle layer like `L`. Practice `M2` until smooth.
:::

## Phase 2 Summary

| Algorithm | Name | Replaces |
|-----------|------|----------|
| `R U2 R' U' R U' R'` | Anti-Sune | Repeated sexy (OC) |
| `R U R' U' R' F R2 U' R' U' R U R' F'` | T-Perm | Niklas (PC) |
| `F R U' R' U' R U R' F' R U R' U' R' F R F'` | Y-Perm | Niklas diagonal (PC) |
| `M2 U M U2 M' U M2` | Ua | Sune+U (PE) |
| `M2 U' M U2 M' U' M2` | Ub | Sune+U (PE) |


# Phase 3: Complete 2-Look CFOP (+6 Algorithms)

Every OLL and PLL case now solved in **one algorithm**.

## OLL Corners: 4 New Cases

![Pi](figures/generated/oll_pi.svg){ width=15% }
![Headlights](figures/generated/oll_headlights.svg){ width=15% }
![Chameleon](figures/generated/oll_chameleon.svg){ width=15% }
![Bowtie](figures/generated/oll_bowtie.svg){ width=15% }

::: algorithm
| Case | Algorithm | Notes |
|------|-----------|-------|
| Pi (0 yellow, Π on front/back) | `f (R U R' U') f' F (R U R' U') F'` | Line + Hook — zero new triggers |
| Headlights (0 yellow, headlights L+R) | `R2 D R' U2 R D' R' U2 R'` | Hold headlights on **left** |
| Chameleon (2 diagonal yellow) | `r U R' U' r' F R F'` | Wide `r` sexy variant |
| Bowtie (2 diagonal yellow) | `F' r U R' U' r' F R` | Rearranged Chameleon |
:::

**All 7 corner OLL cases:**

![Sune](figures/generated/oll_sune.svg){ width=12% }
![Anti-Sune](figures/generated/oll_antisune.svg){ width=12% }
![Pi](figures/generated/oll_pi.svg){ width=12% }
![Headlights](figures/generated/oll_headlights.svg){ width=12% }
![Chameleon](figures/generated/oll_chameleon.svg){ width=12% }
![Bowtie](figures/generated/oll_bowtie.svg){ width=12% }
![Solved](figures/generated/oll_solved.svg){ width=12% }

## PLL Edges: 2 New Cases

![H-Perm](figures/generated/pll_hperm.svg){ width=15% }
![Z-Perm](figures/generated/pll_zperm.svg){ width=15% }

::: algorithm
| Case | Algorithm |
|------|-----------|
| H-Perm (opposite swap) | `M2 U' M2 U2 M2 U' M2` |
| Z-Perm (adjacent swap) | `M' U' M2 U' M2 U' M' U2 M2` |
:::

::: tip
**H vs Z:** No edges match after any U turn. Opposite colors facing each other = H. Adjacent colors = Z.
:::


# Algorithm Reference

## Phase 1: Beginner (~6)

| Algorithm | Name |
|-----------|------|
| `R U R' U'` | Sexy Move |
| `L' U' L U` | Lefty |
| `F (R U R' U') F'` | F-sexy-F' (OE) |
| `R U R' U R U2 R'` | Sune (PE) |
| `R U' L' U R' U' L` | Niklas (PC) |
| Repeat `(R U R' U')` | Corner orient (OC) |

## Phase 2: CFOP Switch (+5)

| Algorithm | Name |
|-----------|------|
| `R U2 R' U' R U' R'` | Anti-Sune (OC) |
| `R U R' U' R' F R2 U' R' U' R U R' F'` | T-Perm (PC) |
| `F R U' R' U' R U R' F' R U R' U' R' F R F'` | Y-Perm (PC) |
| `M2 U M U2 M' U M2` | Ua (PE) |
| `M2 U' M U2 M' U' M2` | Ub (PE) |

## Phase 3: Full 2-Look (+6)

| Algorithm | Name |
|-----------|------|
| `f (R U R' U') f' F (R U R' U') F'` | Pi (OC) |
| `r U R' U' r' F R F'` | Chameleon (OC) |
| `F' r U R' U' r' F R` | Bowtie (OC) |
| `R2 D R' U2 R D' R' U2 R'` | Headlights (OC) |
| `M2 U' M2 U2 M2 U' M2` | H-Perm (PE) |
| `M' U' M2 U' M2 U' M' U2 M2` | Z-Perm (PE) |

## Progression

| Phase | New | Total | LL Order |
|-------|-----|-------|----------|
| 1: Beginner | ~6 | ~6 | OE → PE → PC → OC |
| 2: CFOP Switch | +5 | ~11 | OE → OC → PC → PE |
| 3: Full 2-Look | +6 | ~17 | OE → OC → PC → PE |


# What's Next

- **F2L:** Replace beginner corner+edge insertion with intuitive pairs — the biggest speed improvement.
- **Full OLL** (57 algs) / **Full PLL** (21 algs): One-algorithm solves for every case.
- **Cross planning:** Plan the entire white cross during 15-second inspection.
- **Look-ahead:** Plan the next step while executing the current one.
