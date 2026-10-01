from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.dependencies import get_db
from app.models import Product
from Rutas.auth import verificar_token, require_role
from sqlalchemy import func

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/", dependencies=[Depends(require_role("admin"))])
def obtener_estadisticas(db: Session = Depends(get_db)):
    total_productos = db.query(Product).count()
    activos = db.query(Product).filter(Product.is_active == True).count()
    inactivos = db.query(Product).filter(Product.is_active == False).count()

    stock_total = db.query(func.sum(Product.stock)).scalar() or 0
    stock_bajo = db.query(Product).filter(Product.stock <= Product.min_stock).count()

    precio_promedio = db.query(func.avg(Product.price)).scalar() or 0

    categorias = db.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    marcas = db.query(Product.brand, func.count(Product.id)).group_by(Product.brand).all()

    proximos_a_vencer = db.query(Product).filter(
        Product.expiration_date != None,
        Product.expiration_date <= datetime.utcnow() + timedelta(days=30)
    ).count()

    recientes = db.query(Product).filter(
        Product.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count() if hasattr(Product, "created_at") else None

    return {
        "total_productos": total_productos,
        "activos": activos,
        "inactivos": inactivos,
        "stock_total": stock_total,
        "stock_bajo": stock_bajo,
        "precio_promedio": round(precio_promedio, 2),
        "categorias": categorias,
        "marcas": marcas,
        "proximos_a_vencer": proximos_a_vencer,
        "recientes": recientes
    }
