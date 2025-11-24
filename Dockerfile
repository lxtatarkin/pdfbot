FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# ===== system deps =====
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    fontconfig \
    libfreetype6 \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    libreoffice-core \
    libreoffice-headless \
    fonts-dejavu-core \
    ghostscript \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

# ===== окружение LibreOffice =====
ENV SAL_USE_VCLPLUGIN=gen \
    VCL_PLUGIN=gen \
    SAL_FORCEDPI=96 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# копируем весь проект (включая init_fonts.sh, который создадим ниже)
COPY . .

# делаем скрипт исполняемым
RUN chmod +x /app/init_fonts.sh

CMD ["bash", "/app/init_fonts.sh"]