#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
GUIDE_DIR="$PROJECT_DIR/guide"

# Generate SVG diagrams
echo "Generating diagrams..."
uv run cubepath-diagrams

# Ensure build directory exists
mkdir -p "$GUIDE_DIR/build"

cd "$GUIDE_DIR"

# Build PDF via typst
echo "Building PDF..."
pandoc cubepath.md \
  --defaults defaults/pdf.yaml \
  2>&1

echo ""
echo "Build complete:"
echo "  PDF:  $GUIDE_DIR/build/cubepath.pdf"
