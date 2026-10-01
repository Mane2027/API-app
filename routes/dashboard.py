from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.dependencies import get_db
from app.models import Product
from Rutas.auth import verificar_token, require_role

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/chart", dependencies=[Depends(require_role("admin"))])
def datos_dashboard(db: Session = Depends(get_db)):
    # -----------------------------
    # Productos
    # -----------------------------
    total_productos = db.query(Product).count()
    activos = db.query(Product).filter(Product.is_active == True).count()
    inactivos = db.query(Product).filter(Product.is_active == False).count()

    # -----------------------------
    # Stock
    # -----------------------------
    stock_total = db.query(func.sum(Product.stock)).scalar() or 0
    stock_bajo = db.query(Product).filter(Product.stock <= Product.min_stock).count()

    # -----------------------------
    # Categorías
    # -----------------------------
    categorias = db.query(
        Product.category,
        func.count(Product.id)
    ).group_by(Product.category).all()

    # -----------------------------
    # Marcas
    # -----------------------------
    marcas = db.query(
        Product.brand,
        func.count(Product.id)
    ).group_by(Product.brand).all()

    # -----------------------------
    # Respuesta para Chart.js
    # -----------------------------
    return {
        "productos": {
            "total": total_productos,
            "activos": activos,
            "inactivos": inactivos
        },
        "stock": {
            "total": stock_total,
            "bajo": stock_bajo
        },
        "categorias": categorias,
        "marcas": marcas
    }
