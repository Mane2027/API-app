from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel

from app.dependencies import get_db
from app.models import Product, ProductHistory
from Rutas.auth import verificar_token, require_role
from Rutas.logs import registrar_log

router = APIRouter(prefix="/productos", tags=["Productos"])

# -----------------------------
# Esquema Pydantic
# -----------------------------
class ProductSchema(BaseModel):
    sku: str
    name: str
    description: str | None = None
    brand: str
    category: str = "otro"
    price: float
    cost: float | None = None
    stock: int = 0
    min_stock: int = 5
    expiration_date: str | None = None
    is_active: bool = True


# -----------------------------
# Rutas protegidas
# -----------------------------

# 🟢 Ruta accesible para cualquier usuario autenticado
@router.get("/", dependencies=[Depends(verificar_token)])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


# 🔴 Solo ADMIN puede crear productos
@router.post("/", dependencies=[Depends(require_role("admin"))])
def create_product(data: ProductSchema, db: Session = Depends(get_db)):
    payload = verificar_token()

    if db.query(Product).filter_by(sku=data.sku).first():
        raise HTTPException(status_code=409, detail="SKU ya registrado")

    if data.expiration_date:
        data.expiration_date = datetime.strptime(data.expiration_date, "%Y-%m-%d").date()

    product = Product(**data.dict())
    db.add(product)
    db.commit()
    db.refresh(product)

    registrar_log(db, payload["sub"], "crear_producto", f"SKU: {data.sku}")

    return product


# 🟢 Ruta accesible para cualquier usuario autenticado
@router.get("/{product_id}", dependencies=[Depends(verificar_token)])
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


# 🔴 Solo ADMIN puede actualizar productos
@router.put("/{product_id}", dependencies=[Depends(require_role("admin"))])
def update_product(product_id: int, data: ProductSchema, db: Session = Depends(get_db)):
    payload = verificar_token()

    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if data.expiration_date:
        data.expiration_date = datetime.strptime(data.expiration_date, "%Y-%m-%d").date()

    # Historial de cambios
    for key, value in data.dict(exclude_unset=True).items():
        old_value = getattr(product, key)
        new_value = value

        if old_value != new_value:
            history = ProductHistory(
                product_id=product_id,
                field=key,
                old_value=str(old_value),
                new_value=str(new_value),
                changed_by=payload["sub"]
            )
            db.add(history)

        setattr(product, key, new_value)

    db.commit()
    db.refresh(product)

    registrar_log(db, payload["sub"], "actualizar_producto", f"ID: {product_id}")

    return product


# 🔴 Solo ADMIN puede eliminar productos
@router.delete("/{product_id}", dependencies=[Depends(require_role("admin"))])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    payload = verificar_token()

    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    db.delete(product)
    db.commit()

    registrar_log(db, payload["sub"], "eliminar_producto", f"ID: {product_id}")

    return {"message": "Producto eliminado correctamente"}


# -----------------------------
# Filtros avanzados
# -----------------------------
@router.get("/filtrar", dependencies=[Depends(verificar_token)])
def filtrar_productos(
    categoria: str | None = None,
    marca: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    activos: bool | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    if categoria:
        query = query.filter(Product.category == categoria)

    if marca:
        query = query.filter(Product.brand == marca)

    if min_price:
        query = query.filter(Product.price >= min_price)

    if max_price:
        query = query.filter(Product.price <= max_price)

    if activos is not None:
        query = query.filter(Product.is_active == activos)

    return query.all()


# -----------------------------
# Paginación
# -----------------------------
@router.get("/paginacion", dependencies=[Depends(verificar_token)])
def paginar_productos(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    offset = (page - 1) * limit
    productos = db.query(Product).offset(offset).limit(limit).all()

    total = db.query(Product).count()

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
        "data": productos
    }
