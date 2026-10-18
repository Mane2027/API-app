FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////app/data/database.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear carpeta de la base de datos (sin cambiar usuario)
RUN mkdir -p /app/data

# Ejecutar como root (evita el error en Codespaces)
# USER appuser   <-- eliminar esta línea
