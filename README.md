# Cubepath

A Rubik's Cube guide from Beginner to 2-Look CFOP, with a smooth 3-phase transition that eliminates the dead zone between methods.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pandoc](https://pandoc.org/) >= 3.0
- [typst](https://typst.app/) (for PDF output)

## Build

```bash
# Generate SVG diagrams + build PDF
bash scripts/build.sh
```

Output: `guide/build/cubepath.pdf`

## Generate Diagrams Only

```bash
uv run cubepath-diagrams
```

Outputs SVG diagrams to `guide/figures/generated/`.

## Project Structure

```
cubepath/
├── guide/
│   ├── cubepath.md              # Guide source (markdown)
│   ├── metadata.yaml            # Pandoc metadata
│   ├── defaults/                # Pandoc build configs
│   └── figures/generated/       # SVG diagrams
├── src/cubepath/
│   └── diagrams.py              # SVG diagram generator
└── scripts/
    └── build.sh                 # Build script
```
