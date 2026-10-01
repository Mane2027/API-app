from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.dependencies import get_db
from app.models import Product
from pydantic import BaseModel
from Rutas.auth import verificar_token, require_role

router = APIRouter(prefix="/productos", tags=["Productos"])

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
    if db.query(Product).filter_by(sku=data.sku).first():
        raise HTTPException(status_code=409, detail="SKU ya registrado")

    if data.expiration_date:
        data.expiration_date = datetime.strptime(data.expiration_date, "%Y-%m-%d").date()

    product = Product(**data.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
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
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if data.expiration_date:
        data.expiration_date = datetime.strptime(data.expiration_date, "%Y-%m-%d").date()

    for key, value in data.dict(exclude_unset=True).items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


# 🔴 Solo ADMIN puede eliminar productos
@router.delete("/{product_id}", dependencies=[Depends(require_role("admin"))])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    db.delete(product)
    db.commit()
    return {"message": "Producto eliminado correctamente"}
