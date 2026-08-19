#!/usr/bin/env bash
# Copy the generated SVG diagrams into the app's public assets.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/guide/figures/generated"
DST="$ROOT/app/public/diagrams"
rm -rf "$DST"
mkdir -p "$DST"
cp -R "$SRC/oll" "$SRC/pll" "$SRC/oll-full" "$SRC/pll-full" "$SRC/steps" "$SRC/notation" "$DST/"
echo "Synced $(find "$DST" -name '*.svg' | wc -l | tr -d ' ') diagrams to app/public/diagrams"
