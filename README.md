# API REST — Sistema de Inventario Tienda de Belleza (Python  + Docker)

Backend en **Python** (Flask), construido con **programación orientada a objetos**
(clases `User`, `Product`, `AuthService`, `UserService`, `ProductService`), que expone
API REST con los métodos `GET`, `POST`, `PUT` y `DELETE` para gestionar el **inventario
de divina Essence**: usuarios (con autenticación JWT) y productos (maquillaje,
cuidado facial, cuidado capilar, cuidado corporal, perfumería, uñas, accesorios).
Usa SQLite embebido a través de SQLAlchemy, por lo que corre en un único contenedor
Docker, sin necesitar un servicio de base de datos aparte.

## Archivos del proyecto
```
app.py            -> Toda la aplicación: configuración, modelos, servicios y rutas
requirements.txt  -> Dependencias de Python
Dockerfile        -> Imagen para contenerizar la API
README.md         -> Este archivo
```

## Arquitectura interna (POO), dentro de app.py
- **Modelos** (`Usuarios`, `Productos`): clases ORM de SQLAlchemy que representan las tablas.
- **Servicios** (`Servicio de autorizacion`, `Servicio al usuario`, `Servicio de productos`): clases con la lógica
  de negocio y el acceso a datos.
- **Rutas**: funciones Flask que reciben la petición HTTP y delegan en los servicios.
- **ApiError**: excepción propia con código HTTP, capturada por un manejador global.

Flujo de cada petición: `ruta -> service -> modelo (SQLAlchemy) -> base de datos`.

## Modelo de datos

### Usuario (`users`)
| Campo    | Tipo               | Notas                                    |
|----------|--------------------|--------------------------------------------|
| Nombre     | string             | obligatorio                                 |
| email    | string             | obligatorio, único                          |
| Contraseña | string (hash)      | obligatorio, encriptado con bcrypt          |
| rol     | admin \| vendedor  | por defecto `vendedor`                      |

### Producto (`products`)
| Campo            | Tipo    | Notas                                                       |
|-------------------|---------|----------------------------------------------------------------|
| Código               | string  | obligatorio, único (código interno del producto)                |
| nombre              | string  | obligatorio                                                      |
| descripcion       | text    | opcional                                                          |
| marca             | string  | obligatorio (marca: Maybelline, L'Oréal, Nivea, etc.)            |
| categoria         | string  | maquillaje, cuidado_facial, cuidado_capilar, cuidado_corporal, perfumeria, unas, accesorios, otro |
| precio           | float   | obligatorio, precio de venta                                     |
| costo              | float   | opcional, costo de adquisición (para calcular margen)            |
| stock             | integer | cantidad disponible, por defecto 0                                |
| min_stock         | integer | umbral de bajo stock, por defecto 5                               |
| fecha de vencimiento   | date    | opcional, formato `YYYY-MM-DD`                                    |
| esta activo         | boolean | baja lógica del producto, por defecto true                       |
| tiene baja existencia     | boolean | calculado automáticamente (stock <= min_stock), solo en respuestas|

## Ejecución con Docker

```bash
docker build -t fastapi_inventario:v1.0 .
docker run --name fastapi3 -p 8000:8000 fastapi_inventario:v1.0
```

La API queda disponible en `http://localhost:8000`. La base de datos SQLite
(`database.db`) se crea automáticamente dentro del contenedor al iniciar.

> Nota: al ser SQLite dentro del contenedor, los datos se pierden si el contenedor
> se elimina. Para persistirlos, monta un volumen:
> `docker run -p 8000:8000 -v $(pwd)/data:/app/data -e DATABASE_URL=sqlite:////app/data/database.db inventario-tienda-belleza`

### Variables de entorno opcionales
| Variable                        | Descripción                                 | Valor por defecto        |
|----------------------------------|------------------------------------------------|----------------------------|
| SECRET_KEY                      | Clave secreta de Flask                        | dev-secret-key            |
| JWT_SECRET_KEY                  | Clave para firmar los tokens JWT              | dev-jwt-secret-key        |
| JWT_ACCESS_TOKEN_EXPIRES_HOURS  | Horas de validez del token                    | 8                          |
| DATABASE_URL                    | Cadena de conexión (SQLite, o MySQL/Postgres) | sqlite:///database.db     |

### Ejecución local sin Docker (opcional)
```bash
python -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Endpoints

### Autenticación
| Método | Ruta                | Descripción                        |
|--------|----------------------|--------------------------------------|
| POST   | /api/auth/register   | Registra un nuevo usuario del sistema|
| POST   | /api/auth/login      | Autentica y devuelve un token JWT    |

### Usuarios — requiere header `Authorization: Bearer <token>`
| Método | Ruta             | Descripción              |
|--------|-------------------|---------------------------|
| GET    | /api/users        | Lista todos los usuarios  |
| GET    | /api/users/:id    | Consulta un usuario       |
| POST   | /api/users        | Crea un usuario           |
| PUT    | /api/users/:id    | Actualiza un usuario      |
| DELETE | /api/users/:id    | Elimina un usuario        |

### Productos — requiere header `Authorization: Bearer <token>`
| Método | Ruta                | Descripción                                |
|--------|----------------------|------------------------------------------------|
| GET    | /api/products        | Lista productos del inventario (admite filtros) |
| GET    | /api/products/:id    | Consulta un producto                            |
| POST   | /api/products        | Crea un producto                                |
| PUT    | /api/products/:id    | Actualiza un producto (ej. precio, stock)       |
| DELETE | /api/products/:id    | Elimina un producto                             |

**Filtros disponibles en `GET /api/products` (query params):**
- `?category=maquillaje` — filtra por categoría
- `?brand=Nivea` — filtra por marca
- `?lowStock=true` — solo productos con stock en o por debajo del mínimo
- `?search=labial` — busca por nombre (coincidencia parcial)

Se pueden combinar, ej: `GET /api/products?category=cuidado_facial&lowStock=true`

## Prueba con Postman / Insomnia / curl

1. Registrar usuario:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Carolina Gomez","email":"carolina@tiendabelleza.com","contraseña":"123456","rol":"admin"}'
```

2. Iniciar sesión (copia el `token` de la respuesta):
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"carolina@tiendabelleza.com","password":"123456"}'
```

3. Usar el token en las siguientes peticiones:
```bash
curl -X POST http://localhost:8000/api/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -d '{"sku":"MKP-001","name":"Labial Mate Rojo Pasion","brand":"Maybelline","category":"maquillaje","price":35000,"stock":25,"expiration_date":"2027-06-30"}'

curl "http://localhost:8000/api/products?lowStock=true" \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

También puedes importar estas mismas peticiones en Postman o Insomnia, o probar los
`GET` directamente desde el navegador.

## Seguridad implementada
- Contraseñas encriptadas con `bcrypt` (nunca se guardan ni se devuelven en texto plano).
- Autenticación mediante **JWT**: las rutas de usuarios y productos exigen un token válido.
- Decorador `role_required('admin')` disponible en `app.py` para restringir endpoints
  (por ejemplo, eliminar productos o usuarios) a un rol específico, si se desea aplicar.
- Validación de SKU único para evitar productos duplicados en el inventario.
- Manejo centralizado de errores (`ApiError`) con códigos HTTP apropiados
  (400, 401, 403, 404, 409, 500).
