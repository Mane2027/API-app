from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy import func

from app.dependencies import get_db
from app.models import Product, Provider, Purchase, PurchaseDetail, InventoryMovement
from Rutas.auth import verificar_token, require_role
from Rutas.logs import registrar_log
from Rutas.alertas import generar_alerta

router = APIRouter(prefix="/compras", tags=["Compras"])


# ---------------------------------------------------------
# 📌 REGISTRAR UNA COMPRA A PROVEEDOR
# ---------------------------------------------------------
@router.post("/", dependencies=[Depends(require_role("admin"))])
def registrar_compra(data: PurchaseSchema, db: Session = Depends(get_db)):
    payload = verificar_token()

    proveedor = db.query(Provider).get(data.provider_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    total_compra = 0
    detalles = []

    # Validar productos y calcular total
    for item in data.items:
        producto = db.query(Product).get(item.product_id)
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no existe")

        total_compra += item.price * item.quantity
        detalles.append((producto, item.quantity, item.price))

    # Crear compra
    compra = Purchase(
        total=total_compra,
        provider_id=data.provider_id,
        user=payload["sub"]
    )
    db.add(compra)
    db.commit()
    db.refresh(compra)

    # Registrar detalle + aumentar stock + movimiento
    for producto, cantidad, precio in detalles:
        detalle = PurchaseDetail(
            purchase_id=compra.id,
            product_id=producto.id,
            quantity=cantidad,
            price=precio
        )
        db.add(detalle)

        anterior = producto.stock
        nuevo = anterior + cantidad
        producto.stock = nuevo

        movimiento = InventoryMovement(
            product_id=producto.id,
            movement_type="entrada",
            quantity=cantidad,
            previous_stock=anterior,
            new_stock=nuevo,
            performed_by=payload["sub"]
        )
        db.add(movimiento)

        generar_alerta(db, producto)

    db.commit()

    registrar_log(db, payload["sub"], "compra", f"Compra ID {compra.id}, total {total_compra}")

    return {
        "message": "Compra registrada correctamente",
        "compra_id": compra.id,
        "total": total_compra
    }


# ---------------------------------------------------------
# 📌 LISTAR COMPRAS
# ---------------------------------------------------------
@router.get("/", dependencies=[Depends(verificar_token)])
def listar_compras(db: Session = Depends(get_db)):
    return db.query(Purchase).order_by(Purchase.date.desc()).all()


# ---------------------------------------------------------
# 📌 DETALLE DE UNA COMPRA
# ---------------------------------------------------------
@router.get("/{compra_id}", dependencies=[Depends(verificar_token)])
def detalle_compra(compra_id: int, db: Session = Depends(get_db)):
    compra = db.query(Purchase).get(compra_id)
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")

    return {
        "compra": compra,
        "detalles": compra.details
    }
