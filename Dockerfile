FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# ===== system deps: LibreOffice + шрифты + Tesseract =====
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    ghostscript \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    fontconfig \
    libfreetype6 \
    ttf-mscorefonts-installer \
    && rm -rf /var/lib/apt/lists/*

# ===== настройка шрифтов =====
# отключаем субпиксельное сглаживание и включаем более "жёсткий" хинтинг
RUN mkdir -p /etc/fonts && \
    printf '%s\n' \
'<?xml version="1.0"?>' \
'<!DOCTYPE fontconfig SYSTEM "fonts.dtd">' \
'<fontconfig>' \
'  <match target="font">' \
'    <edit name="rgba" mode="assign"><const>none</const></edit>' \
'    <edit name="hinting" mode="assign"><bool>true</bool></edit>' \
'    <edit name="hintstyle" mode="assign"><const>hintfull</const></edit>' \
'  </match>' \
'</fontconfig>' \
    > /etc/fonts/local.conf && \
    fc-cache -f -v

# ===== окружение для LibreOffice (стабильный рендер) =====
ENV SAL_USE_VCLPLUGIN=gen \
    VCL_PLUGIN=gen \
    SAL_FORCEDPI=96 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код бота
COPY . .

CMD ["python", "bot.py"]