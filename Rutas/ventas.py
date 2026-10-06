from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.dependencies import get_db
from app.models import (
    Provider, Product,
    Purchase, PurchaseDetail,
    Sale, SaleDetail
)
from Rutas.auth import verificar_token, require_role

router = APIRouter(prefix="/reportes", tags=["Reportes"])


# ---------------------------------------------------------
# 📌 REPORTE: COMPRAS POR PROVEEDOR
# ---------------------------------------------------------
@router.get("/compras/proveedor/{provider_id}", dependencies=[Depends(require_role("admin"))])
def compras_por_proveedor(provider_id: int, db: Session = Depends(get_db)):
    proveedor = db.query(Provider).get(provider_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    compras = db.query(Purchase).filter(Purchase.provider_id == provider_id).all()

    total_invertido = sum(c.total for c in compras)

    productos = (
        db.query(
            Product.name,
            func.sum(PurchaseDetail.quantity).label("cantidad"),
            func.sum(PurchaseDetail.quantity * PurchaseDetail.price).label("subtotal")
        )
        .join(PurchaseDetail, PurchaseDetail.product_id == Product.id)
        .join(Purchase, Purchase.id == PurchaseDetail.purchase_id)
        .filter(Purchase.provider_id == provider_id)
        .group_by(Product.name)
        .all()
    )

    productos_formato = [
        {
            "nombre": p.name,
            "cantidad_comprada": p.cantidad,
            "subtotal": p.subtotal
        }
        for p in productos
    ]

    return {
        "proveedor": proveedor.name,
        "total_compras": len(compras),
        "total_invertido": total_invertido,
        "productos": productos_formato,
        "compras": compras
    }


# ---------------------------------------------------------
# 📌 REPORTE: COMPRAS POR PRODUCTO
# ---------------------------------------------------------
@router.get("/compras/producto/{product_id}", dependencies=[Depends(require_role("admin"))])
def compras_por_producto(product_id: int, db: Session = Depends(get_db)):
    producto = db.query(Product).get(product_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    detalles = (
        db.query(
            PurchaseDetail.quantity,
            PurchaseDetail.price,
            Purchase.date
        )
        .join(Purchase, Purchase.id == PurchaseDetail.purchase_id)
        .filter(PurchaseDetail.product_id == product_id)
        .all()
    )

    total_cantidad = sum(d.quantity for d in detalles)
    total_invertido = sum(d.quantity * d.price for d in detalles)

    return {
        "producto": producto.name,
        "total_cantidad": total_cantidad,
        "total_invertido": total_invertido,
        "compras": detalles
    }


# ---------------------------------------------------------
# 📌 REPORTE: COMPRAS POR FECHA
# ---------------------------------------------------------
@router.get("/compras/fecha", dependencies=[Depends(require_role("admin"))])
def compras_por_fecha(fecha: str, db: Session = Depends(get_db)):
    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")

    compras = db.query(Purchase).filter(
        func.date(Purchase.date) == fecha_dt.date()
    ).all()

    total = sum(c.total for c in compras)

    return {
        "fecha": fecha,
        "total_compras": len(compras),
        "total_invertido": total,
        "compras": compras
    }


# ---------------------------------------------------------
# 📌 REPORTE GLOBAL DE COMPRAS
# ---------------------------------------------------------
@router.get("/compras/global", dependencies=[Depends(require_role("admin"))])
def compras_global(db: Session = Depends(get_db)):
    compras = db.query(Purchase).all()
    total = sum(c.total for c in compras)

    return {
        "total_compras": len(compras),
        "total_invertido": total,
        "compras": compras
    }


# ---------------------------------------------------------
# 📌 REPORTE: VENTAS POR FECHA
# ---------------------------------------------------------
@router.get("/ventas/fecha", dependencies=[Depends(require_role("admin"))])
def ventas_por_fecha(fecha: str, db: Session = Depends(get_db)):
    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")

    ventas = db.query(Sale).filter(
        func.date(Sale.date) == fecha_dt.date()
    ).all()

    total = sum(v.total for v in ventas)

    return {
        "fecha": fecha,
        "total_ventas": len(ventas),
        "total_generado": total,
        "ventas": ventas
    }


# ---------------------------------------------------------
# 📌 REPORTE: VENTAS POR PRODUCTO
# ---------------------------------------------------------
@router.get("/ventas/producto/{product_id}", dependencies=[Depends(require_role("admin"))])
def ventas_por_producto(product_id: int, db: Session = Depends(get_db)):
    producto = db.query(Product).get(product_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    detalles = (
        db.query(
            SaleDetail.quantity,
            SaleDetail.price,
            Sale.date
        )
        .join(Sale, Sale.id == SaleDetail.sale_id)
        .filter(SaleDetail.product_id == product_id)
        .all()
    )

    total_cantidad = sum(d.quantity for d in detalles)
    total_generado = sum(d.quantity * d.price for d in detalles)

    return {
        "producto": producto.name,
        "total_cantidad": total_cantidad,
        "total_generado": total_generado,
        "ventas": detalles
    }


# ---------------------------------------------------------
# 📌 REPORTE GLOBAL DE VENTAS
# ---------------------------------------------------------
@router.get("/ventas/global", dependencies=[Depends(require_role("admin"))])
def ventas_global(db: Session = Depends(get_db)):
    ventas = db.query(Sale).all()
    total = sum(v.total for v in ventas)

    return {
        "total_ventas": len(ventas),
        "total_generado": total,
        "ventas": ventas
    }
