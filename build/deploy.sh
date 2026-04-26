#!/usr/bin/env bash
# deploy.sh — stage the built atlas into a sibling assets repo.
#
# Bifurcated deployment:
#   - This repo (naklitechie/india-2500) holds the source: data/, validators/,
#     build/, web/template.html, tests/, contribute/.
#   - The assets repo (naklitechie/assets, deployed as assets.chiragpatnaik.com)
#     holds the built artifacts: india-history.html and the PNG companions.
#
# Usage:
#   ./build/deploy.sh <path-to-assets-repo>
#
# Example:
#   ./build/deploy.sh ../assets
#
# What this does:
#   1. Validates the corpus (all 6 validators must PASS).
#   2. Rebuilds web/india-history.html, web/shell.html, and PNG companions.
#   3. Copies the built artifacts into the target assets repo.
#   4. Stops short of git add / commit / push — the user runs those.

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <path-to-assets-repo>"
  echo ""
  echo "example: $0 ../assets"
  exit 2
fi

ASSETS_DIR="$1"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -d "$ASSETS_DIR" ]; then
  echo "error: $ASSETS_DIR does not exist"
  exit 2
fi

echo "==> validating corpus"
cd "$REPO_ROOT"
for v in validators/validate_*.py; do
  python3 "$v" >/dev/null
done
echo "    all 6 validators PASS"

echo "==> rebuilding HTML"
python3 build/build_html.py >/dev/null
echo "    web/india-history.html (single-file) and web/shell.html (runtime-fetch)"

echo "==> rebuilding PNG companions"
if python3 build/build_png.py >/dev/null 2>&1; then
  echo "    web/india-history.png and web/india-history-square.png"
else
  echo "    skipped (build_png.py failed; matplotlib may not be available)"
fi

echo "==> staging artifacts to $ASSETS_DIR"
cp "$REPO_ROOT/web/india-history.html" "$ASSETS_DIR/"
[ -f "$REPO_ROOT/web/india-history.png" ] && cp "$REPO_ROOT/web/india-history.png" "$ASSETS_DIR/"
[ -f "$REPO_ROOT/web/india-history-square.png" ] && cp "$REPO_ROOT/web/india-history-square.png" "$ASSETS_DIR/"

echo ""
echo "Staged. Review and commit from the assets repo:"
echo "  cd $ASSETS_DIR"
echo "  git status"
echo "  git diff --stat"
echo "  git add india-history.html india-history*.png"
echo "  git commit -m 'india-history.html: <summary>'"
echo "  git push"
