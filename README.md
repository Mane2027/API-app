# API REST — Inventario Tienda de Belleza (FastAPI + Docker)

Backend en Python (FastAPI) para gestionar el inventario de la tienda Divina Essence:
productos, usuarios, ventas, compras, proveedores, alertas de stock, reportes y auditoría.

**Tecnologías:** FastAPI · Uvicorn · SQLAlchemy · SQLite · Pydantic · JWT (python-jose) · bcrypt · ReportLab · openpyxl · Docker

## Estructura

```
.
├── main.py            # app, CORS, routers y admin inicial
├── database.py        # motor y sesión (lee DATABASE_URL)
├── models.py          # tablas
├── dependencies.py    # get_db
├── Rutas/             # un archivo por módulo (auth, usuarios, productos, ventas, ...)
├── utils/email_sender.py
├── tests/test_api.py
├── requirements.txt / requirements-dev.txt
├── Dockerfile / .dockerignore / .env.example
```

## Configuración

Copia `.env.example` a `.env` y completa al menos `JWT_SECRET_KEY`, `ADMIN_USERNAME` y `ADMIN_PASSWORD`.
Al arrancar, si no existe ningún administrador, se crea con esas credenciales.

## Ejecutar con Docker

```bash
docker build -t fastapi_inventario:v2.0 .
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  fastapi_inventario:v2.0
```

La base de datos queda en `./data/database.db`. La API queda en <http://localhost:8000> y la documentación en `/docs` y `/redoc`.

## Ejecutar sin Docker

```bash
pip install -r requirements.txt
set -a; source .env; set +a      # carga las variables
uvicorn main:app --reload
```

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

## Autenticación

- `POST /usuarios/login` (JSON `{"username","password"}`) → `access_token` (JWT, vence en 3 h por defecto).
- Enviar `Authorization: Bearer <token>` en las demás rutas.
- Roles: `admin` (todo) y `user` (consultar y registrar ventas).
- `POST /usuarios/registro` solo lo puede usar un administrador.

## Endpoints

| Módulo | Endpoints | Acceso |
|---|---|---|
| Usuarios | `POST /usuarios/login`, `GET /usuarios/me` | autenticado |
| | `POST /usuarios/registro`, `GET /usuarios`, `GET/PUT/DELETE /usuarios/{id}` | admin |
| Productos | `GET /productos` (filtros `category`, `brand`, `lowStock`, `search`), `GET /productos/filtrar`, `GET /productos/paginacion`, `GET /productos/{id}` | autenticado |
| | `POST /productos`, `PUT/DELETE /productos/{id}` | admin |
| Ventas | `GET /ventas`, `GET /ventas/{id}`, `POST /ventas` | autenticado |
| Compras | `GET /compras`, `GET /compras/{id}` | autenticado |
| | `POST /compras` | admin |
| Inventario | `GET /inventario/resumen`, `/inventario/bajo`, `/inventario/historial/{id}` | autenticado |
| | `POST /inventario/entrada/{id}?cantidad=`, `POST /inventario/salida/{id}?cantidad=` | admin |
| Proveedores | `GET /proveedores`, `GET /proveedores/{id}` | autenticado |
| | `POST /proveedores`, `PUT/DELETE /proveedores/{id}` | admin |
| Alertas | `GET /alertas` | autenticado |
| Dashboard | `GET /dashboard/chart` | admin |
| Reportes | `GET /reportes/excel`, `/reportes/pdf`, `/reportes/compras/{global,fecha,proveedor/{id},producto/{id}}`, `/reportes/ventas/{global,fecha,producto/{id}}` | admin |
| Logs | `GET /logs` | admin |

Ejemplo de venta (el precio lo toma el servidor desde la base de datos):

```json
POST /ventas
{ "items": [ { "product_id": 1, "quantity": 2 } ] }
```

Ejemplo de compra:

```json
POST /compras
{ "provider_id": 1, "items": [ { "product_id": 1, "quantity": 10, "price": 12000 } ] }
```

## Seguridad

- Contraseñas con bcrypt; JWT firmado con `JWT_SECRET_KEY` (sin clave fija se genera una temporal y se avisa).
- Registro de usuarios restringido a administradores; los roles se validan en cada ruta.
- CORS limitado a `CORS_ORIGINS`.
- Validación de datos con Pydantic (cantidades > 0, precios ≥ 0, emails válidos).
- Ventas, compras y movimientos de inventario son transacciones atómicas; el stock no puede quedar negativo.
- El contenedor corre sin privilegios de root.

