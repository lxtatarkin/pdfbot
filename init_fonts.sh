#!/usr/bin/env bash
set -e

FONT_VOL_DIR="/fonts-private"
FONT_TARGET_DIR="/usr/share/fonts/truetype/custom"

mkdir -p "$FONT_VOL_DIR" "$FONT_TARGET_DIR"

echo "=== Checking fonts in volume $FONT_VOL_DIR ==="

download_font() {
  local name="$1"
  local url="$2"

  if [ -z "$url" ]; then
    echo "  [WARN] URL for $name is empty, skip"
    return
  fi

  if [ -f "$FONT_VOL_DIR/$name" ]; then
    echo "  [OK] $name already exists in volume"
  else
    echo "  [DL] Downloading $name from $url"
    wget -q -O "$FONT_VOL_DIR/$name" "$url" || echo "  [ERR] Failed to download $name"
  fi
}

# === ЗДЕСЬ ПОДСТАВЬ СВОИ ССЫЛКИ НА ФАЙЛЫ ===
download_font "calibri.ttf"   "https://drive.google.com/file/d/19x3QhVTT52L-QSIXP5Xu5vLfgAqUOvFO/view?usp=drive_link"
download_font "calibrib.ttf"  "https://drive.google.com/file/d/1k6tACGWs40fxtWbLJ3PVRio8u1yY1UWu/view?usp=drive_link"
download_font "calibrii.ttf"  "https://drive.google.com/file/d/1f2uMGAhN2A8Y9Cv-0l0HRelo2dMDTXHI/view?usp=drive_link"
download_font "cambria.ttc"   "https://drive.google.com/file/d/1UFCFw6NKP5lGXC3JuenBmG2JXhv2qQ5S/view?usp=drive_link"
download_font "calibril.ttf"  "https://drive.google.com/file/d/1c0y4Hi7kcYHutvUPEgBEOpVMZma7m3Kk/view?usp=drive_link"
download_font "calibrili.ttf" "https://drive.google.com/file/d/1QhdGfqWKTqGUgQVfKnfiZW-p3Hz2bWeZ/view?usp=drive_link"
download_font "calibriz.ttf"  "https://drive.google.com/file/d/1gwCKoFp0GY3jSzCtRSNkPSJlhQLFcfP-/view?usp=drive_link"
download_font "cambriab.ttf"  "https://drive.google.com/file/d/1Uv55K0Vsi-9-Xrn2A6klVSnbUj79nsAh/view?usp=drive_link"
download_font "cambriai.ttf"  "https://drive.google.com/file/d/1UFCFw6NKP5lGXC3JuenBmG2JXhv2qQ5S/view?usp=drive_link"
download_font "cambriaz.ttf"  "https://drive.google.com/file/d/1H-kSgWbcHPa2f3-9AOms-L9t7wAkB5pX/view?usp=drive_link"
download_font "times.ttf"     "https://drive.google.com/file/d/1rF-FQBtQjth-YU7xjpUS0jwAjijSJkBF/view?usp=drive_link"
download_font "timesbd.ttf"   "https://drive.google.com/file/d/1qe5_bKPmmq-kH1rRSscINUuGPhTSw3UH/view?usp=drive_link"
download_font "timesbi.ttf"   "https://drive.google.com/file/d/17_bYK5E2LOJ-dR68LO3Z8TJIkY6wMd_r/view?usp=drive_link"
download_font "timesi.ttf"    "https://drive.google.com/file/d/1KxIjLKRK0QJ1d8NZFjx5bBZiMwHYpPP9/view?usp=drive_link"

echo "=== Copying fonts into system dir $FONT_TARGET_DIR ==="

cp "$FONT_VOL_DIR"/*.ttf "$FONT_TARGET_DIR" 2>/dev/null || true
cp "$FONT_VOL_DIR"/*.ttc "$FONT_TARGET_DIR" 2>/dev/null || true

echo "=== Updating font cache ==="
fc-cache -f -v || true

echo "=== Fonts visible in system (Calibri/Cambria) ==="
fc-list | grep -i "calibri\|cambria" || true

echo "=== Starting bot ==="
exec python bot.py