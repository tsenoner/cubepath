#!/usr/bin/env bash
# Build the guide PDF, ship it into the app, and stamp its inputs.
#
# Diagram generation deliberately does NOT live here. It used to, which made
# `make build-guide` quietly regenerate guide/figures/generated/ — an input to
# the *app* — without syncing it, while `make diagrams` regenerated and synced.
# The Makefile now expresses that as `build-guide: diagrams`, so the tree has
# one owner and this script only runs pandoc.
#
# The copy into app/public/ and the stamp are here rather than in the Makefile
# so they cannot be separated from the compile: the stamp asserts that the
# *shipped* PDF is current, so a build that wrote the stamp without copying
# would be a false green.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
GUIDE_DIR="$PROJECT_DIR/guide"

mkdir -p "$GUIDE_DIR/build"

cd "$GUIDE_DIR"

echo "Building PDF..."
pandoc cubepath.md \
  --defaults defaults/pdf.yaml \
  2>&1

# Vercel builds only `cd app && npm ci && npm run build` — no pandoc there — so
# the PDF the app serves at /cubepath.pdf has to be a committed artifact.
cp "$GUIDE_DIR/build/cubepath.pdf" "$PROJECT_DIR/app/public/cubepath.pdf"

# Records what that PDF was built from; tests/test_guide.py fails the gate when
# the guide source moves on without a rebuild.
python3 "$SCRIPT_DIR/guide_stamp.py" --write

echo ""
echo "Build complete:"
echo "  PDF:  $GUIDE_DIR/build/cubepath.pdf"
echo "  App:  $PROJECT_DIR/app/public/cubepath.pdf"
