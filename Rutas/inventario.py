from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from dependencies import get_db
from models import InventoryMovement, Product
from Rutas.alertas import enviar_alertas_por_correo, generar_alerta
from Rutas.auth import require_role, verificar_token
from Rutas.logs import registrar_log

router = APIRouter(prefix="/inventario", tags=["Inventario"])


def _mover(db, background, payload, product_id, cantidad, tipo):
    producto = db.get(Product, product_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    anterior = producto.stock
    if tipo == "salida":
        if anterior < cantidad:
            raise HTTPException(status_code=400, detail="Stock insuficiente")
        nuevo = anterior - cantidad
    else:
        nuevo = anterior + cantidad

    producto.stock = nuevo
    db.add(
        InventoryMovement(
            product_id=product_id,
            movement_type=tipo,
            quantity=cantidad,
            previous_stock=anterior,
            new_stock=nuevo,
            performed_by=payload["sub"],
        )
    )
    mensaje = generar_alerta(db, producto)
    db.commit()  # stock + movimiento + alerta en una sola transacción

    if mensaje:
        background.add_task(enviar_alertas_por_correo, [mensaje])

    signo = "+" if tipo == "entrada" else "-"
    registrar_log(db, payload["sub"], f"{tipo}_inventario", f"Producto {product_id}, {signo}{cantidad}")

    return {
        "message": "Entrada registrada" if tipo == "entrada" else "Salida registrada",
        "producto": producto.name,
        "stock_anterior": anterior,
        "stock_nuevo": nuevo,
    }

@router.get("/kardex/{product_id}", dependencies=[Depends(verificar_token)])
def kardex(product_id: int, db: Session = Depends(get_db)):
    producto = db.get(Product, product_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    movimientos = (
        db.query(InventoryMovement)
        .filter_by(product_id=product_id)
        .order_by(InventoryMovement.timestamp.asc())
        .all()
    )

    saldo = 0
    kardex = []

    for mov in movimientos:
        if mov.movement_type == "entrada":
            saldo += mov.quantity
        else:
            saldo -= mov.quantity

        kardex.append({
            "fecha": mov.timestamp,
            "tipo": mov.movement_type,
            "cantidad": mov.quantity,
            "stock_anterior": mov.previous_stock,
            "stock_nuevo": mov.new_stock,
            "saldo_kardex": saldo,
            "usuario": mov.performed_by,
        })

    return {
        "producto": producto.name,
        "kardex": kardex,
        "total_movimientos": len(kardex),
        "saldo_final": saldo,
    }
@router.post("/entrada/{product_id}")
def entrada_inventario(
    product_id: int,
    background: BackgroundTasks,
    cantidad: int = Query(..., gt=0),  # antes aceptaba negativos y 0
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    return _mover(db, background, payload, product_id, cantidad, "entrada")


@router.post("/salida/{product_id}")
def salida_inventario(
    product_id: int,
    background: BackgroundTasks,
    cantidad: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    return _mover(db, background, payload, product_id, cantidad, "salida")


@router.get("/resumen", dependencies=[Depends(verificar_token)])
def resumen_inventario(db: Session = Depends(get_db)):
    return {
        "total_productos": db.query(Product).count(),
        "unidades_en_stock": db.query(func.sum(Product.stock)).scalar() or 0,
        "valor_inventario": db.query(func.sum(Product.stock * Product.price)).scalar() or 0,
        "stock_bajo": db.query(Product).filter(Product.stock <= Product.min_stock).count(),
        "agotados": db.query(Product).filter(Product.stock == 0).count(),
    }


@router.get("/bajo", dependencies=[Depends(verificar_token)])
def productos_bajo_stock(db: Session = Depends(get_db)):
    return (
        db.query(Product)
        .filter(Product.stock <= Product.min_stock)
        .order_by(Product.stock)
        .all()
    )


@router.get("/historial/{product_id}", dependencies=[Depends(verificar_token)])
def historial_inventario(product_id: int, db: Session = Depends(get_db)):
    if not db.get(Product, product_id):
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return (
        db.query(InventoryMovement)
        .filter_by(product_id=product_id)
        .order_by(InventoryMovement.timestamp.desc())
        .all()
    )


   
