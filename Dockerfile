FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////app/data/database.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Instalar herramientas necesarias para useradd
RUN apt-get update && apt-get install -y --no-install-recommends \
    shadow \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios y carpeta de la base de datos
RUN useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser
