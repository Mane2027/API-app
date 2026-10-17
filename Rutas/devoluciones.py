from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from dependencies import get_db
from models import (
    Product,
    Sale,
    SaleDetail,
    Purchase,
    PurchaseDetail,
    InventoryMovement,
)
from Rutas.alertas import enviar_alertas_por_correo, generar_alerta
from Rutas.auth import require_role, verificar_token
from Rutas.logs import registrar_log

router = APIRouter(prefix="/devoluciones", tags=["Devoluciones"])


# ---------------------------
# DEVOLUCIÓN DE VENTA
# ---------------------------
@router.post("/venta/{detalle_id}")
def devolver_venta(
    detalle_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    detalle = db.get(SaleDetail, detalle_id)
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle de venta no encontrado")

    producto = db.get(Product, detalle.product_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    anterior = producto.stock
    nuevo = anterior + detalle.quantity

    producto.stock = nuevo

    db.add(
        InventoryMovement(
            product_id=producto.id,
            movement_type="entrada",
            quantity=detalle.quantity,
            previous_stock=anterior,
            new_stock=nuevo,
            performed_by=payload["sub"],
        )
    )

    mensaje = generar_alerta(db, producto)
    db.commit()

    if mensaje:
        background.add_task(enviar_alertas_por_correo, [mensaje])

    registrar_log(
        db,
        payload["sub"],
        "devolucion_venta",
        f"Detalle {detalle_id}, +{detalle.quantity}",
    )

    return {
        "message": "Devolución de venta registrada",
        "producto": producto.name,
        "cantidad_devuelta": detalle.quantity,
        "stock_nuevo": nuevo,
    }


# ---------------------------
# DEVOLUCIÓN DE COMPRA
# ---------------------------
@router.post("/compra/{detalle_id}")
def devolver_compra(
    detalle_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    detalle = db.get(PurchaseDetail, detalle_id)
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle de compra no encontrado")

    producto = db.get(Product, detalle.product_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    anterior = producto.stock

    if anterior < detalle.quantity:
        raise HTTPException(
            status_code=400,
            detail="No se puede devolver: el stock actual es menor a la cantidad comprada",
        )

    nuevo = anterior - detalle.quantity
    producto.stock = nuevo

    db.add(
        InventoryMovement(
            product_id=producto.id,
            movement_type="salida",
            quantity=detalle.quantity,
            previous_stock=anterior,
            new_stock=nuevo,
            performed_by=payload["sub"],
        )
    )

    mensaje = generar_alerta(db, producto)
    db.commit()

    if mensaje:
        background.add_task(enviar_alertas_por_correo, [mensaje])

    registrar_log(
        db,
        payload["sub"],
        "devolucion_compra",
        f"Detalle {detalle_id}, -{detalle.quantity}",
    )

    return {
        "message": "Devolución de compra registrada",
        "producto": producto.name,
        "cantidad_devuelta": detalle.quantity,
        "stock_nuevo": nuevo,
    }
