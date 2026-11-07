# ==============================================================================
# Football Simulator - Multi-stage Production Dockerfile
# Hem FastAPI Web Sunucusu hem de Celery Worker bu image üzerinden çalışır.
# ==============================================================================
FROM python:3.11-slim

# Temel ortam değişkenleri
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Sistem paketlerini kur (PostgreSQL binary bağımlılıkları ve curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını ve veri dizinlerini kopyala
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Varsayılan port
EXPOSE 8000

# Varsayılan komut (Docker Compose ile ezilebilir)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
