# Imagen base
FROM python:3.10

# Crear carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiar todo el proyecto al contenedor
COPY ..
# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto
EXPOSE 8000

# Comando para ejecutar FastAPI con Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
