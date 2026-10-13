from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from dependencies import get_db
from models import (
    InventoryMovement, Product, ProductHistory, PurchaseDetail, SaleDetail,
)
from Rutas.auth import require_role, verificar_token
from Rutas.logs import registrar_log

router = APIRouter(prefix="/productos", tags=["Productos"])


class ProductSchema(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    brand: str = Field(min_length=1, max_length=100)
    category: str = Field(default="otro", max_length=30)
    price: float = Field(ge=0)
    cost: float | None = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    min_stock: int = Field(default=5, ge=0)
    expiration_date: date | None = None  # "YYYY-MM-DD"
    is_active: bool = True


# NOTA: las rutas fijas (/filtrar, /paginacion) van ANTES de /{product_id};
# si no, FastAPI intenta convertir "filtrar" a entero y responde 422.

# ---------------------------------------------------------
# LISTAR (con filtros opcionales: category, brand, lowStock, search)
# ---------------------------------------------------------
@router.get("/", dependencies=[Depends(verificar_token)])
def get_products(
    category: str | None = None,
    brand: str | None = None,
    low_stock: bool | None = Query(None, alias="lowStock"),
    search: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    if brand:
        query = query.filter(Product.brand == brand)
    if low_stock:
        query = query.filter(Product.stock <= Product.min_stock)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.ilike(like),
                Product.sku.ilike(like),
                Product.brand.ilike(like),
                Product.description.ilike(like),
            )
        )
    return query.order_by(Product.id).all()


@router.get("/filtrar", dependencies=[Depends(verificar_token)])
def filtrar_productos(
    categoria: str | None = None,
    marca: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    activos: bool | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if categoria:
        query = query.filter(Product.category == categoria)
    if marca:
        query = query.filter(Product.brand == marca)
    if min_price is not None:  # antes "if min_price:" ignoraba el valor 0
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if activos is not None:
        query = query.filter(Product.is_active == activos)
    return query.all()


@router.get("/paginacion", dependencies=[Depends(verificar_token)])
def paginar_productos(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(Product).count()
    productos = (
        db.query(Product).order_by(Product.id).offset((page - 1) * limit).limit(limit).all()
    )
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
        "data": productos,
    }


# ---------------------------------------------------------
# CRUD
# ---------------------------------------------------------
@router.post("/")
def create_product(
    data: ProductSchema,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    if db.query(Product).filter_by(sku=data.sku).first():
        raise HTTPException(status_code=409, detail="SKU ya registrado")

    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)

    registrar_log(db, payload["sub"], "crear_producto", f"SKU: {data.sku}")
    return product


@router.get("/{product_id}", dependencies=[Depends(verificar_token)])
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@router.put("/{product_id}")
def update_product(
    product_id: int,
    data: ProductSchema,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if data.sku != product.sku and db.query(Product).filter_by(sku=data.sku).first():
        raise HTTPException(status_code=409, detail="SKU ya registrado")

    # Historial de cambios campo por campo
    for key, new_value in data.model_dump().items():
        old_value = getattr(product, key)
        if old_value != new_value:
            db.add(
                ProductHistory(
                    product_id=product_id,
                    field=key,
                    old_value=str(old_value),
                    new_value=str(new_value),
                    changed_by=payload["sub"],
                )
            )
        setattr(product, key, new_value)

    db.commit()
    db.refresh(product)

    registrar_log(db, payload["sub"], "actualizar_producto", f"ID: {product_id}")
    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Si ya tiene ventas, compras o movimientos, borrarlo dejaría los reportes huérfanos.
    tiene_historial = (
        db.query(SaleDetail).filter_by(product_id=product_id).first()
        or db.query(PurchaseDetail).filter_by(product_id=product_id).first()
        or db.query(InventoryMovement).filter_by(product_id=product_id).first()
    )
    if tiene_historial:
        raise HTTPException(
            status_code=409,
            detail="El producto tiene ventas, compras o movimientos; desactívalo (is_active=false) en lugar de eliminarlo",
        )

    db.delete(product)
    db.commit()

    registrar_log(db, payload["sub"], "eliminar_producto", f"ID: {product_id}")
    return {"message": "Producto eliminado correctamente"}
   
