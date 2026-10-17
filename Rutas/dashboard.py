from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from dependencies import get_db
from models import Sale, SaleDetail, Purchase, Provider, Product

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/filtrado")
def dashboard_filtrado(
    start: str,
    end: str,
    db: Session = Depends(get_db)
):
    # Ventas filtradas
    ventas = (
        db.query(
            func.to_char(Sale.date, "YYYY-MM-DD").label("date"),
            func.sum(Sale.total).label("total")
        )
        .filter(Sale.date >= start, Sale.date <= end)
        .group_by("date")
        .order_by("date")
        .all()
    )

    # Compras filtradas
    compras = (
        db.query(
            Provider.name,
            func.sum(Purchase.total).label("total")
        )
        .join(Provider, Provider.id == Purchase.provider_id)
        .filter(Purchase.date >= start, Purchase.date <= end)
        .group_by(Provider.name)
        .all()
    )

    return {
        "ventas": [{"date": d, "total": float(t)} for d, t in ventas],
        "compras": [{"provider": p, "total": float(t)} for p, t in compras],
    }
@router.get("/")
def obtener_dashboard(db: Session = Depends(get_db)):

    # Ventas por mes
    ventas = (
        db.query(
            func.to_char(Sale.date, "YYYY-MM").label("month"),
            func.sum(Sale.total).label("total")
        )
        .group_by("month")
        .order_by("month")
        .all()
    )

    # Compras por proveedor
    compras = (
        db.query(
            Provider.name,
            func.sum(Purchase.total).label("total")
        )
        .join(Provider, Provider.id == Purchase.provider_id)
        .group_by(Provider.name)
        .all()
    )

    # Productos más vendidos
    top = (
        db.query(
            Product.name,
            func.sum(SaleDetail.quantity).label("quantity")
        )
        .join(SaleDetail, SaleDetail.product_id == Product.id)
        .group_by(Product.name)
        .order_by(func.sum(SaleDetail.quantity).desc())
        .limit(5)
        .all()
    )

    # Stock bajo
    bajo = db.query(Product).filter(Product.stock < 10).all()

    return {
        "sales_per_month": [{"month": m, "total": float(t)} for m, t in ventas],
        "purchases_by_provider": [{"provider": p, "total": float(t)} for p, t in compras],
        "top_products": [{"name": n, "quantity": int(q)} for n, q in top],
        "low_stock": bajo,
    }
