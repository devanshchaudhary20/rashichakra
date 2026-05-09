#!/usr/bin/env bash
# Downloads SIL OFL fonts:
#   Inter (regular + bold) — body text
#   Playfair Display (bold) — display / sign names / dates

set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)/fonts"
mkdir -p "$DIR"

download() {
  local url="$1"
  local out="$2"
  if [[ -f "$out" ]]; then
    echo "[fonts] already have $(basename "$out")"
    return 0
  fi
  echo "[fonts] downloading $(basename "$out")"
  curl -fsSL "$url" -o "$out"
}

# Inter is a variable font in google/fonts (square brackets URL-encoded)
download \
  "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf" \
  "$DIR/Inter-Regular.ttf"

# Same file, used as 'Bold' alias (PIL truetype just reads weight from variation;
# for simplicity we point both to the variable font and let the renderer use it as-is)
cp "$DIR/Inter-Regular.ttf" "$DIR/Inter-Bold.ttf" || true

download \
  "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf" \
  "$DIR/PlayfairDisplay-Bold.ttf"

echo "[fonts] done."
