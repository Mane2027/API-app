FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Servidor de producción (gunicorn) sirviendo la app Flask (app.py -> variable "app")
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]
