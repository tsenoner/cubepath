#!/usr/bin/env bash
# Copy the generated SVG diagrams into the app's public assets.
#
# Every subdirectory is copied, deliberately: the list used to be hardcoded,
# which meant a newly generated group (f2l/ was the one that caught it) was
# silently never shipped while this script still printed a count and exited 0.
# tests/test_diagrams.py derives its guarded set from the same tree for the
# same reason.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/guide/figures/generated"
DST="$ROOT/app/public/diagrams"
rm -rf "$DST"
mkdir -p "$DST"
# A trailing slash makes `cp -R` copy the CONTENTS, flattening every group into
# one directory, so the glob is stripped back to bare directory names.
shopt -s nullglob
subdirs=()
for d in "$SRC"/*/; do subdirs+=("${d%/}"); done
if [ ${#subdirs[@]} -eq 0 ]; then
  echo "no diagram subdirectories in $SRC — run 'make diagrams'" >&2
  exit 1
fi
cp -R "${subdirs[@]}" "$DST/"
echo "Synced $(find "$DST" -name '*.svg' | wc -l | tr -d ' ') diagrams to app/public/diagrams"
