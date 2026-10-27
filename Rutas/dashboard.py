from collections import defaultdict
from datetime import date, datetime, time
 
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
 
from dependencies import get_db
from models import Product, Purchase, Sale, SaleDetail
from Rutas.auth import verificar_token
 
 
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
 
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
 
 
def _mes_atras(d: date, n: int) -> date:
    """Primer día del mes que queda n meses antes de d."""
    m = d.month - 1 - n
    return date(d.year + m // 12, m % 12 + 1, 1)
 
 
@router.get("/resumen", dependencies=[Depends(verificar_token)])
def resumen(meses: int = Query(6, ge=1, le=12), db: Session = Depends(get_db)):
    hoy = date.today()
    inicio_mes = datetime.combine(hoy.replace(day=1), time.min)
 
    # IMPORTANTE: usa aquí la misma condición de "producto activo" que tenías
    # antes (el nombre del campo puede ser active, is_active, activo...).
    activos = Product.active == True  # noqa: E712
 
    # Tarjetas (estado actual y mes en curso: no dependen del filtro)
    total_productos = db.query(func.count(Product.id)).filter(activos).scalar() or 0
    unidades = db.query(func.coalesce(func.sum(Product.stock), 0)).filter(activos).scalar() or 0
    valor_inventario = (
        db.query(func.coalesce(func.sum(Product.stock * func.coalesce(Product.cost, 0)), 0))
        .filter(activos).scalar() or 0
    )
    stock_bajo = (
        db.query(func.count(Product.id))
        .filter(activos, Product.stock <= Product.min_stock).scalar() or 0
    )
    ventas_mes = (
        db.query(func.coalesce(func.sum(Sale.total), 0)).filter(Sale.date >= inicio_mes).scalar() or 0
    )
    compras_mes = (
        db.query(func.coalesce(func.sum(Purchase.total), 0)).filter(Purchase.date >= inicio_mes).scalar() or 0
    )
 
    # Barras: ventas y compras de los últimos `meses` meses (incluye el actual)
    inicios = [_mes_atras(hoy, n) for n in range(meses - 1, -1, -1)]
    desde = datetime.combine(inicios[0], time.min)
    ventas_por_mes, compras_por_mes = defaultdict(float), defaultdict(float)
    for v in db.query(Sale).filter(Sale.date >= desde).all():
        ventas_por_mes[(v.date.year, v.date.month)] += v.total
    for c in db.query(Purchase).filter(Purchase.date >= desde).all():
        compras_por_mes[(c.date.year, c.date.month)] += c.total
    mensual = [
        {
            "mes": MESES[m.month - 1],
            "ventas": round(ventas_por_mes[(m.year, m.month)], 2),
            "compras": round(compras_por_mes[(m.year, m.month)], 2),
        }
        for m in inicios
    ]
 
    # Dona: unidades en stock por categoría (estado actual)
    por_categoria = [
        {"categoria": cat or "otro", "unidades": int(u or 0)}
        for cat, u in db.query(Product.category, func.sum(Product.stock))
        .filter(activos).group_by(Product.category).all()
        if (u or 0) > 0
    ]
 
    # Productos con más salidas en el mismo periodo del filtro
    filas = (
        db.query(SaleDetail.product_id, func.sum(SaleDetail.quantity).label("total"))
        .join(Sale, SaleDetail.sale_id == Sale.id)
        .filter(Sale.date >= desde)
        .group_by(SaleDetail.product_id)
        .order_by(func.sum(SaleDetail.quantity).desc())
        .limit(5).all()
    )
    nombres = {p.id: p.name for p in db.query(Product).all()}
    top = [
        {"producto": nombres.get(pid, f"Producto #{pid}"), "unidades": int(total)}
        for pid, total in filas
    ]
 
    return {
        "tarjetas": {
            "productos": total_productos,
            "unidades": int(unidades),
            "valor_inventario": round(float(valor_inventario), 2),
            "stock_bajo": stock_bajo,
            "ventas_mes": round(float(ventas_mes), 2),
            "compras_mes": round(float(compras_mes), 2),
        },
        "mensual": mensual,
        "por_categoria": por_categoria,
        "top_productos": top,
    }
 
