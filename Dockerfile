FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install fastapi uvicorn sqlalchemy python-jose[cryptography]
COPY main.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
