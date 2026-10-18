from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from dependencies import get_db
from models import Sale, SaleDetail, Purchase, Provider, Product

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def construir_dashboard(db: Session, start: str | None = None, end: str | None = None):
    filtrar = bool(start and end)

    # Ventas por mes
    mes = func.strftime("%Y-%m", Sale.date)
    q_ventas = db.query(mes.label("month"), func.sum(Sale.total).label("total"))
    if filtrar:
        q_ventas = q_ventas.filter(
            func.date(Sale.date) >= start, func.date(Sale.date) <= end
        )
    ventas = q_ventas.group_by(mes).order_by(mes).all()

    # Compras por proveedor
    q_compras = db.query(
        Provider.name, func.sum(Purchase.total).label("total")
    ).join(Provider, Provider.id == Purchase.provider_id)
    if filtrar:
        q_compras = q_compras.filter(
            func.date(Purchase.date) >= start, func.date(Purchase.date) <= end
        )
    compras = q_compras.group_by(Provider.name).all()

    # Productos más vendidos
    q_top = db.query(
        Product.name, func.sum(SaleDetail.quantity).label("quantity")
    ).join(SaleDetail, SaleDetail.product_id == Product.id)
    if filtrar:
        q_top = q_top.join(Sale, Sale.id == SaleDetail.sale_id).filter(
            func.date(Sale.date) >= start, func.date(Sale.date) <= end
        )
    top = (
        q_top.group_by(Product.name)
        .order_by(func.sum(SaleDetail.quantity).desc())
        .limit(5)
        .all()
    )

    # Stock bajo
    bajo = db.query(Product).filter(Product.stock < 10).all()

    return {
        "sales_per_month": [{"month": m, "total": float(t or 0)} for m, t in ventas],
        "purchases_by_provider": [{"provider": p, "total": float(t or 0)} for p, t in compras],
        "top_products": [{"name": n, "quantity": int(q or 0)} for n, q in top],
        "low_stock": [{"id": p.id, "name": p.name, "stock": p.stock} for p in bajo],
    }


@router.get("/filtrado")
def dashboard_filtrado(start: str, end: str, db: Session = Depends(get_db)):
    return construir_dashboard(db, start, end)


@router.get("/stats")
def estadisticas(db: Session = Depends(get_db)):
    # Promedio de ventas por día
    diario = (
        db.query(func.sum(Sale.total).label("t"))
        .group_by(func.date(Sale.date))
        .subquery()
    )
    promedio = db.query(func.avg(diario.c.t)).scalar() or 0

    # Producto con más unidades vendidas
    rentable = (
        db.query(Product.name, func.sum(SaleDetail.quantity).label("q"))
        .join(SaleDetail, SaleDetail.product_id == Product.id)
        .group_by(Product.name)
        .order_by(func.sum(SaleDetail.quantity).desc())
        .first()
    )

    # Proveedor con mayor volumen de compras
    proveedor = (
        db.query(Provider.name, func.sum(Purchase.total).label("total"))
        .join(Provider, Provider.id == Purchase.provider_id)
        .group_by(Provider.name)
        .order_by(func.sum(Purchase.total).desc())
        .first()
    )

    return {
        "promedio_diario": round(float(promedio), 2),
        "producto_rentable": {"name": rentable[0] if rentable else "—"},
        "proveedor_top": {
            "name": proveedor[0] if proveedor else "—",
            "total": float(proveedor[1]) if proveedor else 0,
        },
    }


# Sin barra final, para evitar la redirección 307 detrás del proxy
@router.get("")
@router.get("/", include_in_schema=False)
def obtener_dashboard(db: Session = Depends(get_db)):
    return construir_dashboard(db)
