FROM python:3.11-slim

WORKDIR /usr/src/backend

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# 必要なパッケージとTesseract OCR、日本語言語データをインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-jpn \
    libtesseract-dev \
    poppler-utils \
    wget \
    --no-install-recommends && \
    mkdir -p /usr/share/tesseract-ocr/4.00/tessdata && \
    wget https://github.com/tesseract-ocr/tessdata_best/raw/main/jpn.traineddata -P /usr/share/tesseract-ocr/4.00/tessdata/ && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# pip のアップグレード
RUN pip install --upgrade pip

# 必要な Python ライブラリをインストール
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# ソースコードをコンテナにコピー
COPY . .

# アプリケーションの起動コマンド
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
