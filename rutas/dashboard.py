from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.dependencies import get_db
from app.models import Product, InventoryMovement
from Rutas.auth import verificar_token, require_role

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/chart", dependencies=[Depends(require_role("admin"))])
def datos_dashboard(db: Session = Depends(get_db)):
    # ---------------------------------------------------------
    # 📌 Productos
    # ---------------------------------------------------------
    total_productos = db.query(Product).count()
    activos = db.query(Product).filter(Product.is_active == True).count()
    inactivos = db.query(Product).filter(Product.is_active == False).count()

    # ---------------------------------------------------------
    # 📌 Stock
    # ---------------------------------------------------------
    stock_total = db.query(func.sum(Product.stock)).scalar() or 0
    stock_bajo = db.query(Product).filter(Product.stock <= Product.min_stock).count()
    stock_agotado = db.query(Product).filter(Product.stock == 0).count()
    stock_critico = db.query(Product).filter(Product.stock < (Product.min_stock / 2)).count()

    # Valor total del inventario
    valor_total = db.query(func.sum(Product.stock * Product.price)).scalar() or 0

    # ---------------------------------------------------------
    # 📌 Categorías
    # ---------------------------------------------------------
    categorias = db.query(
        Product.category,
        func.count(Product.id)
    ).group_by(Product.category).all()

    # ---------------------------------------------------------
    # 📌 Marcas
    # ---------------------------------------------------------
    marcas = db.query(
        Product.brand,
        func.count(Product.id)
    ).group_by(Product.brand).all()

    # ---------------------------------------------------------
    # 📌 Productos próximos a vencer (30 días)
    # ---------------------------------------------------------
    proximos_vencer = db.query(Product).filter(
        Product.expiration_date != None,
        Product.expiration_date <= datetime.utcnow() + timedelta(days=30)
    ).count()

    # ---------------------------------------------------------
    # 📌 Productos recientes (últimos 7 días)
    # ---------------------------------------------------------
    recientes = None
    if hasattr(Product, "created_at"):
        recientes = db.query(Product).filter(
            Product.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()

    # ---------------------------------------------------------
    # 📌 Movimientos de inventario (si existe InventoryMovement)
    # ---------------------------------------------------------
    movimientos_entrada = 0
    movimientos_salida = 0

    try:
        movimientos_entrada = db.query(InventoryMovement).filter(
            InventoryMovement.movement_type == "entrada"
        ).count()

        movimientos_salida = db.query(InventoryMovement).filter(
            InventoryMovement.movement_type == "salida"
        ).count()
    except:
        pass  # Si no existe la tabla, no falla

    # ---------------------------------------------------------
    # 📌 Respuesta final para Chart.js
    # ---------------------------------------------------------
    return {
        "productos": {
            "total": total_productos,
            "activos": activos,
            "inactivos": inactivos,
            "recientes": recientes
        },
        "stock": {
            "total": stock_total,
            "bajo": stock_bajo,
            "critico": stock_critico,
            "agotado": stock_agotado,
            "valor_total": valor_total
        },
        "categorias": categorias,
        "marcas": marcas,
        "vencimiento": {
            "proximos_vencer": proximos_vencer
        },
        "movimientos": {
            "entradas": movimientos_entrada,
            "salidas": movimientos_salida
        }
    }
