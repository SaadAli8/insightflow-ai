# Single image used by the API, the Celery workers, and the Kafka consumer.
# Each container just runs a different command (see docker-compose.yml).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps:
#  - tesseract-ocr  -> OCR for images / scanned PDFs
#  - poppler-utils  -> pdf2image needs it to rasterize PDF pages
#  - libxml2/libxslt-> trafilatura (lxml) HTML parsing
#  - gcc            -> build a few wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        poppler-utils \
        libxml2-dev \
        libxslt1-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Default command = API. Workers override this in docker-compose.yml.
CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", "-b", "0.0.0.0:8000", \
     "--timeout", "120"]
