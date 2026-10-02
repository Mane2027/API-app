from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.dependencies import get_db
from app.models import Product, Sale, SaleDetail, InventoryMovement
from Rutas.auth import verificar_token, require_role
from Rutas.logs import registrar_log
from Rutas.alertas import generar_alerta
from Rutas import ventas

app.include_router(ventas.router)

router = APIRouter(prefix="/ventas", tags=["Ventas"])


# ---------------------------------------------------------
# 📌 REGISTRAR UNA VENTA
# ---------------------------------------------------------
@router.post("/", dependencies=[Depends(require_role("admin"))])
def registrar_venta(data: SaleSchema, db: Session = Depends(get_db)):
    payload = verificar_token()

    total_venta = 0
    detalles = []

    # Validar stock y calcular total
    for item in data.items:
        producto = db.query(Product).get(item.product_id)
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no existe")

        if producto.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para {producto.name}")

        total_venta += producto.price * item.quantity
        detalles.append((producto, item.quantity))

    # Crear venta
    venta = Sale(
        total=total_venta,
        user=payload["sub"]
    )
    db.add(venta)
    db.commit()
    db.refresh(venta)

    # Registrar detalle + descontar stock + movimientos
    for producto, cantidad in detalles:
        detalle = SaleDetail(
            sale_id=venta.id,
            product_id=producto.id,
            quantity=cantidad,
            price=producto.price
        )
        db.add(detalle)

        # Movimiento de inventario
        anterior = producto.stock
        nuevo = anterior - cantidad
        producto.stock = nuevo

        movimiento = InventoryMovement(
            product_id=producto.id,
            movement_type="salida",
            quantity=cantidad,
            previous_stock=anterior,
            new_stock=nuevo,
            performed_by=payload["sub"]
        )
        db.add(movimiento)

        # Alertas automáticas
        generar_alerta(db, producto)

    db.commit()

    registrar_log(db, payload["sub"], "venta", f"Venta ID {venta.id}, total {total_venta}")

    return {
        "message": "Venta registrada correctamente",
        "venta_id": venta.id,
        "total": total_venta
    }


# ---------------------------------------------------------
# 📌 LISTAR TODAS LAS VENTAS
# ---------------------------------------------------------
@router.get("/", dependencies=[Depends(verificar_token)])
def listar_ventas(db: Session = Depends(get_db)):
    return db.query(Sale).order_by(Sale.date.desc()).all()


# ---------------------------------------------------------
# 📌 OBTENER DETALLE DE UNA VENTA
# ---------------------------------------------------------
@router.get("/{venta_id}", dependencies=[Depends(verificar_token)])
def detalle_venta(venta_id: int, db: Session = Depends(get_db)):
    venta = db.query(Sale).get(venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    return {
        "venta": venta,
        "detalles": venta.details
    }


# ---------------------------------------------------------
# 📌 TOP PRODUCTOS MÁS VENDIDOS
# ---------------------------------------------------------
@router.get("/top", dependencies=[Depends(require_role("admin"))])
def top_productos_vendidos(db: Session = Depends(get_db)):
    resultados = (
        db.query(
            Product.id,
            Product.name,
            func.sum(SaleDetail.quantity).label("cantidad_vendida"),
            func.sum(SaleDetail.quantity * SaleDetail.price).label("total_generado")
        )
        .join(SaleDetail, SaleDetail.product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(SaleDetail.quantity).desc())
        .limit(10)
        .all()
    )

    top = [
        {
            "product_id": r.id,
            "nombre": r.name,
            "cantidad_vendida": r.cantidad_vendida,
            "total_generado": r.total_generado
        }
        for r in resultados
    ]

    return {
        "top_productos": top,
        "total_items": len(top)
    }
