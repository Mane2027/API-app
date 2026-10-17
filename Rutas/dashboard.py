from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dependencies import get_db
from models import Sale, Purchase, Product, InventoryMovement
from sqlalchemy import func

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

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
            Purchase.provider_id,
            func.sum(Purchase.total).label("total")
        )
        .group_by(Purchase.provider_id)
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
        "sales_per_month": [{"month": m, "total": t} for m, t in ventas],
        "purchases_by_provider": [{"provider": p, "total": t} for p, t in compras],
        "top_products": [{"name": n, "quantity": q} for n, q in top],
        "low_stock": bajo,
    }
