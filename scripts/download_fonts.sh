#!/usr/bin/env bash
# Downloads SIL OFL fonts:
#   Elms Sans (regular) — body / horoscope text
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

download \
  "https://github.com/mara-aa/elms-sans/raw/main/fonts/ttf/ElmsSans-Regular.ttf" \
  "$DIR/ElmsSans-Regular.ttf"

download \
  "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf" \
  "$DIR/PlayfairDisplay-Bold.ttf"

echo "[fonts] done."
