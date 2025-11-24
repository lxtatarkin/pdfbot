FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# базовые зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    tar \
    fontconfig \
    libfreetype6 \
    libxrender1 \
    libxext6 \
    libxinerama1 \
    libgl1 \
    libglu1-mesa \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# ===== Устанавливаем LibreOffice HEADLESS =====
RUN wget https://download.documentfoundation.org/libreoffice/stable/24.2.3/deb/x86_64/LibreOffice_24.2.3_Linux_x86-64_deb.tar.gz -O /tmp/lo.tar.gz \
    && tar -xvf /tmp/lo.tar.gz -C /tmp \
    && dpkg -i /tmp/LibreOffice_24.2.3.2_Linux_x86-64_deb/DEBS/*.deb \
    && rm -rf /tmp/lo.tar.gz /tmp/LibreOffice*

# шрифты
RUN mkdir -p /usr/share/fonts/truetype/custom

# окружение для headless режима
ENV SAL_USE_VCLPLUGIN=gen
ENV VCL_PLUGIN=gen
ENV DISPLAY=

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]