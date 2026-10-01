from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.dependencies import get_db
from app.models import Product, InventoryMovement
from Rutas.auth import verificar_token, require_role
from Rutas.logs import registrar_log

router = APIRouter(prefix="/inventario", tags=["Inventario"])


# ---------------------------------------------------------
# 📌 ENTRADA DE INVENTARIO
# ---------------------------------------------------------
@router.post("/entrada/{product_id}", dependencies=[Depends(require_role("admin"))])
def entrada_inventario(product_id: int, cantidad: int, db: Session = Depends(get_db)):
    payload = verificar_token()

    producto = db.query(Product).get(product_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    anterior = producto.stock
    nuevo = anterior + cantidad

    producto.stock = nuevo

    movimiento = InventoryMovement(
        product_id=product_id,
        movement_type="entrada",
        quantity=cantidad,
        previous_stock=anterior,
        new_stock=nuevo,
        performed_by=payload["sub"]
    )

    db.add(movimiento)
    db.commit()

    registrar_log(db, payload["sub"], "entrada_inventario", f"Producto {product_id}, +{cantidad}")

    return {
        "message": "Entrada registrada",
        "producto": producto.name,
        "stock_anterior": anterior,
        "stock_nuevo": nuevo
    }


# ---------------------------------------------------------
# 📌 SALIDA DE INVENTARIO
# ---------------------------------------------------------
@router.post("/salida/{product_id}", dependencies=[Depends(require_role("admin"))])
def salida_inventario(product_id: int, cantidad: int, db: Session = Depends(get_db)):
    payload = verificar_token()

    producto = db.query(Product).get(product_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if producto.stock < cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    anterior = producto.stock
    nuevo = anterior - cantidad

    producto.stock = nuevo

    movimiento = InventoryMovement(
        product_id=product_id,
        movement_type="salida",
        quantity=cantidad,
        previous_stock=anterior,
        new_stock=nuevo,
        performed_by=payload["sub"]
    )

    db.add(movimiento)
    db.commit()

    registrar_log(db, payload["sub"], "salida_inventario", f"Producto {product_id}, -{cantidad}")

    return {
        "message": "Salida registrada",
        "producto": producto.name,
        "stock_anterior": anterior,
        "stock_nuevo": nuevo
    }


# ---------------------------------------------------------
# 📌 HISTORIAL DE MOVIMIENTOS
# ---------------------------------------------------------
@router.get("/historial/{product_id}", dependencies=[Depends(verificar_token)])
def historial_inventario(product_id: int, db: Session = Depends(get_db)):
    movimientos = db.query(InventoryMovement).filter_by(product_id=product_id).all()

    if not movimientos:
        raise HTTPException(status_code=404, detail="No hay movimientos registrados")

    return movimientos
