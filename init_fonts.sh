#!/usr/bin/env bash
set -e

# Сначала проверяем, не установлены ли шрифты уже в системе
echo "=== init_fonts: checking if fonts already installed ==="
if fc-list | grep -qi "calibri"; then
  echo "=== init_fonts: fonts already installed, skipping download and install ==="
  echo "=== init_fonts: starting bot ==="
  exec python bot.py
fi

echo "=== init_fonts: fonts not found, continuing installation ==="

# Каталог, куда складываем шрифты (volume / временное хранилище)
FONT_VOL_DIR="/fonts-private"
# Каталог, где система ожидает ttf/otf (LibreOffice будет их видеть через fontconfig)
FONT_TARGET_DIR="/usr/share/fonts/truetype/custom"

mkdir -p "$FONT_VOL_DIR" "$FONT_TARGET_DIR"

echo "=== init_fonts: checking volume at $FONT_VOL_DIR ==="

# Проверяем, есть ли уже какие-то шрифты в volume (например, сохранённые с прошлого запуска через volume)
if ls "$FONT_VOL_DIR"/*.ttf "$FONT_VOL_DIR"/*.ttc "$FONT_VOL_DIR"/*.otf >/dev/null 2>&1; then
  echo "=== init_fonts: fonts already found in volume, skip download ==="
else
  echo "=== init_fonts: no fonts found in volume ==="

  # Если в Railway задана переменная окружения с URL архива шрифтов — скачиваем и распаковываем
  if [ -n "$FONTS_ZIP_URL" ]; then
    echo "=== init_fonts: downloading fonts archive from \$FONTS_ZIP_URL ==="
    echo "    URL: $FONTS_ZIP_URL"

    wget -q -O /tmp/fonts.zip "$FONTS_ZIP_URL" || {
      echo "  [ERR] Failed to download fonts.zip from $FONTS_ZIP_URL"
    }

    if [ -f /tmp/fonts.zip ]; then
      echo "=== init_fonts: unzipping /tmp/fonts.zip into $FONT_VOL_DIR ==="
      unzip -o /tmp/fonts.zip -d "$FONT_VOL_DIR" >/dev/null 2>&1 || echo "  [WARN] unzip failed (maybe archive is empty or corrupted)"
    else
      echo "  [WARN] /tmp/fonts.zip not found after download attempt"
    fi
  else
    echo "=== init_fonts: FONTS_ZIP_URL is not set, skip download ==="
  fi
fi

echo "=== init_fonts: copying fonts into system dir $FONT_TARGET_DIR ==="

# Копируем все ttf/ttc/otf из volume (включая вложенные папки) в системный каталог шрифтов
find "$FONT_VOL_DIR" -maxdepth 5 -type f \( -iname "*.ttf" -o -iname "*.ttc" -o -iname "*.otf" \) \
  -exec cp "{}" "$FONT_TARGET_DIR"/ \; 2>/dev/null || true

echo "=== init_fonts: updating font cache ==="
fc-cache -f -v || true

echo "=== init_fonts: visible core fonts (calibri/cambria) ==="
fc-list | grep -i "calibri\|cambria" || true

echo "=== init_fonts: starting bot ==="
exec python bot.py