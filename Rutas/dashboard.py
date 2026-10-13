from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from dependencies import get_db
from models import InventoryMovement, Product
from Rutas.auth import require_role

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/chart", dependencies=[Depends(require_role("admin"))])
def datos_dashboard(db: Session = Depends(get_db)):
    total_productos = db.query(Product).count()
    activos = db.query(Product).filter(Product.is_active.is_(True)).count()
    inactivos = total_productos - activos

    stock_total = db.query(func.sum(Product.stock)).scalar() or 0
    stock_bajo = db.query(Product).filter(Product.stock <= Product.min_stock).count()
    stock_agotado = db.query(Product).filter(Product.stock == 0).count()
    stock_critico = db.query(Product).filter(Product.stock < (Product.min_stock / 2)).count()
    valor_total = db.query(func.sum(Product.stock * Product.price)).scalar() or 0

    categorias = db.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    marcas = db.query(Product.brand, func.count(Product.id)).group_by(Product.brand).all()

    # expiration_date es Date: se compara con date, no con datetime
    proximos_vencer = (
        db.query(Product)
        .filter(
            Product.expiration_date.is_not(None),
            Product.expiration_date <= date.today() + timedelta(days=30),
        )
        .count()
    )

    recientes = (
        db.query(Product)
        .filter(Product.created_at >= datetime.now() - timedelta(days=7))
        .count()
    )

    entradas = db.query(InventoryMovement).filter(InventoryMovement.movement_type == "entrada").count()
    salidas = db.query(InventoryMovement).filter(InventoryMovement.movement_type == "salida").count()

    return {
        "productos": {
            "total": total_productos,
            "activos": activos,
            "inactivos": inactivos,
            "recientes": recientes,
        },
        "stock": {
            "total": stock_total,
            "bajo": stock_bajo,
            "critico": stock_critico,
            "agotado": stock_agotado,
            "valor_total": valor_total,
        },
        "categorias": [[nombre, n] for nombre, n in categorias],
        "marcas": [[nombre, n] for nombre, n in marcas],
        "vencimiento": {"proximos_vencer": proximos_vencer},
        "movimientos": {"entradas": entradas, "salidas": salidas},
    }

