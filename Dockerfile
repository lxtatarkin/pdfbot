FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# ===== system deps =====
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    fontconfig \
    libfreetype6 \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    ghostscript \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

# ===== базовые corefonts (Arial, Times, Verdana и т.п.) =====
RUN mkdir -p /usr/share/fonts/truetype/msttcore && \
    wget -O /tmp/corefonts.zip https://downloads.sourceforge.net/corefonts/corefonts-1.zip && \
    unzip /tmp/corefonts.zip -d /tmp/corefonts && \
    cp /tmp/corefonts/*.ttf /usr/share/fonts/truetype/msttcore/ || true && \
    rm -rf /tmp/corefonts /tmp/corefonts.zip

# ===== кастомные шрифты (Calibri, Cambria и др.) из папки fonts/ проекта =====
# ВАЖНО: ты сам кладёшь сюда свои .ttf из легального источника (Office и т.п.)
COPY fonts /usr/share/fonts/truetype/custom

# обновляем кеш шрифтов
RUN fc-cache -f -v

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