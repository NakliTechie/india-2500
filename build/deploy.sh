#!/usr/bin/env bash
# deploy.sh — stage the built atlas into a target hosting directory.
#
# Usage:
#   ./build/deploy.sh <path-to-target-directory>
#
# Example:
#   ./build/deploy.sh /path/to/your/hosted/site
#
# What this does:
#   1. Validates the corpus (all 6 validators must PASS).
#   2. Rebuilds web/india-history.html, web/shell.html, and PNG companions.
#   3. Copies the built artifacts into the target directory.
#   4. Injects the host-side page-nav sidebar (depends on /pages.json existing
#      at the host root for the "All" panel; harmless 404 if absent).
#   5. Stops short of git add / commit / push — you run those.

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <path-to-target-directory>"
  exit 2
fi

TARGET_DIR="$1"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -d "$TARGET_DIR" ]; then
  echo "error: $TARGET_DIR does not exist"
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

echo "==> staging artifacts to $TARGET_DIR"
cp "$REPO_ROOT/web/india-history.html" "$TARGET_DIR/"
[ -f "$REPO_ROOT/web/india-history.png" ] && cp "$REPO_ROOT/web/india-history.png" "$TARGET_DIR/"
[ -f "$REPO_ROOT/web/india-history-square.png" ] && cp "$REPO_ROOT/web/india-history-square.png" "$TARGET_DIR/"

echo "==> injecting host-side page-nav sidebar"
python3 "$REPO_ROOT/build/_pagenav-inject.py" "$TARGET_DIR/india-history.html"

echo ""
echo "Staged. Review and publish from $TARGET_DIR yourself."
