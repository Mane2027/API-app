API REST — Sistema de Inventario Tienda de Belleza (FastAPI + Docker)
Backend desarrollado en Python (FastAPI) para gestionar el inventario de la tienda Divina Essence, incluyendo productos, usuarios, ventas, compras, reportes, proveedores, alertas y más.
El sistema está modularizado mediante routers, utiliza SQLAlchemy como ORM y se ejecuta dentro de un contenedor Docker.

Tecnologías utilizadas
*FastAPI — Framework moderno y rápido para APIs REST

*Uvicorn — Servidor ASGI

*SQLAlchemy — ORM para la base de datos

*SQLite — Base de datos embebida

*Pydantic — Validación de datos

*Docker — Contenerización del backend

*JWT — Autenticación 

📦 Estructura del proyecto
Código
.
── main.py
── database.py
── models.py
── dependencies.py
── requirements.txt
── Dockerfile

── routes/
  ── alertas.py
   ── auth.py
   ── compras.py
  ── dashboard.py
   ── inventario.py
   ── logs.py
   ── productos.py
   ── proveedores.py
   ── reportes.py
   ── usuarios.py
   ── ventas.py

── utils/
    └── email_sender.py
 
🧩 Descripción de módulos
*main.py
Punto de entrada de la aplicación.
Incluye:

-instancia de FastAPI
-inclusión de routers
-configuración inicial

*database.py
Configuración de SQLAlchemy:
-motor
-sesión
-creación de tablas

*models.py
Modelos ORM que representan las tablas del sistema:
-productos
-usuarios
-proveedores
-ventas
-compras

*dependencies.py
Dependencias reutilizables:
-sesión de base de datos
-autenticación (si aplica)
*routes/
Carpeta con todos los módulos de rutas organizados por funcionalidad:

-productos
-ventas
-compras
-usuarios
-reportes
-proveedores
-dashboard
-alertas
-logs

*utils/
Funciones auxiliares:
-envío de correos
-utilidades generales

*Docker
Construir la imagen
bash
docker build -t fastapi_inventario:v1.0 .
Ejecutar el contenedor
bash
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e DATABASE_URL=sqlite:///app/data/database.db \
  fastapi_inventario:v1.0
La API queda disponible en:
Código
http://localhost:8000
📡 Endpoints principales
Cada módulo dentro de routes/ expone sus propios endpoints:
/productos
/ventas
/compras
/usuarios
/reportes
/proveedores
/inventario
/dashboard
/alertas
/logs
/auth (si usas JWT)

La documentación automática está disponible en:
Código
/docs
/redoc

Ejecución local sin Docker
bash
pip install -r requirements.txt
uvicorn main:app --reload

Seguridad implementada
-Contraseñas encriptadas 
-Autenticación mediante JWT
-Validación de datos con Pydantic
-Manejo de errores centralizado por FastAPI
