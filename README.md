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

 Autenticación (routes/auth.py)
Método	Ruta	Descripción
POST	/auth/login	Iniciar sesión y obtener token JWT
POST	/auth/register	Registrar usuario (si lo tienes)


👤 Usuarios (routes/usuarios.py)
Método	Ruta	Descripción
GET	/usuarios	Listar usuarios
GET	/usuarios/{id}	Obtener usuario por ID
POST	/usuarios	Crear usuario
PUT	/usuarios/{id}	Actualizar usuario
DELETE	/usuarios/{id}	Eliminar usuario


📦 Productos (routes/productos.py)
Método	Ruta	Descripción
GET	/productos	Listar productos (admite filtros)
GET	/productos/{id}	Obtener producto por ID
POST	/productos	Crear producto
PUT	/productos/{id}	Actualizar producto
DELETE	/productos/{id}	Eliminar producto


Filtros disponibles en GET /productos:

?category=maquillaje

?brand=Nivea

?lowStock=true

?search=labial

🛒 Ventas (routes/ventas.py)
Método	Ruta	Descripción
GET	/ventas	Listar ventas
POST	/ventas	Registrar venta
GET	/ventas/{id}	Obtener venta por ID


🧾 Compras (routes/compras.py)
Método	Ruta	Descripción
GET	/compras	Listar compras
POST	/compras	Registrar compra
GET	/compras/{id}	Obtener compra por ID


🧪 Inventario (routes/inventario.py)
Método	Ruta	Descripción
GET	/inventario/resumen	Resumen general del inventario
GET	/inventario/bajo	Productos con bajo stock


📊 Dashboard (routes/dashboard.py)
Método	Ruta	Descripción
GET	/dashboard	Métricas generales del sistema


🚨 Alertas (routes/alertas.py)
Método	Ruta	Descripción
GET	/alertas	Alertas del sistema


📝 Reportes (routes/reportes.py)
Método	Ruta	Descripción
GET	/reportes/ventas	Reporte de ventas
GET	/reportes/productos	Reporte de productos


🏭 Proveedores (routes/proveedores.py)
Método	Ruta	Descripción
GET	/proveedores	Listar proveedores
POST	/proveedores	Crear proveedor
GET	/proveedores/{id}	Obtener proveedor


📚 Logs (routes/logs.py)
Método	Ruta	Descripción
GET	/logs	Ver logs del sistema



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
