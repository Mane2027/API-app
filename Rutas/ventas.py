from collections import defaultdict
 
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
 
from dependencies import get_db
from models import InventoryMovement, Product, Sale, SaleDetail
from Rutas.alertas import enviar_alertas_por_correo, generar_alerta
from Rutas.auth import verificar_token
from Rutas.logs import registrar_log
 
router = APIRouter(prefix="/ventas", tags=["Ventas"])
 
 
class SaleItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
 
 
class SaleSchema(BaseModel):
    items: list[SaleItem] = Field(min_length=1)
 
 
@router.post("/")
def registrar_venta(
    data: SaleSchema,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    payload: dict = Depends(verificar_token),
):
    # Si el mismo producto viene dos veces, se suman las cantidades
    cantidades: dict[int, int] = defaultdict(int)
    for item in data.items:
        cantidades[item.product_id] += item.quantity
 
    # El precio sale de la base de datos, nunca del cliente
    productos = {}
    for pid, qty in cantidades.items():
        producto = db.get(Product, pid)
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {pid} no existe")
        if not producto.is_active:
            raise HTTPException(status_code=400, detail=f"'{producto.name}' está inactivo")
        if producto.stock < qty:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente de '{producto.name}' (disponible: {producto.stock})",
            )
        productos[pid] = producto
 
    total = round(sum(productos[pid].price * qty for pid, qty in cantidades.items()), 2)
 
    venta = Sale(total=total, user=payload["sub"])
    db.add(venta)
    db.flush()
 
    mensajes = []
    for pid, qty in cantidades.items():
        producto = productos[pid]
        anterior = producto.stock
 
        # Descuento atómico: solo se aplica si todavía hay stock suficiente
        # (evita stock negativo si dos ventas llegan al mismo tiempo)
        actualizado = (
            db.query(Product)
            .filter(Product.id == pid, Product.stock >= qty)
            .update({Product.stock: Product.stock - qty}, synchronize_session=False)
        )
        if actualizado == 0:
            db.rollback()
            raise HTTPException(
                status_code=409, detail=f"Stock insuficiente de '{producto.name}', intenta de nuevo"
            )
        db.refresh(producto)
 
        db.add(SaleDetail(sale_id=venta.id, product_id=pid, quantity=qty, price=producto.price))
        db.add(
            InventoryMovement(
                product_id=pid,
                movement_type="salida",
                quantity=qty,
                previous_stock=anterior,
                new_stock=producto.stock,
                performed_by=payload["sub"],
            )
        )
        mensaje = generar_alerta(db, producto)
        if mensaje:
            mensajes.append(mensaje)
 
    db.commit()
    background.add_task(enviar_alertas_por_correo, mensajes)
 
    registrar_log(db, payload["sub"], "venta", f"Venta ID {venta.id}, total {total}")
    return {"message": "Venta registrada correctamente", "venta_id": venta.id, "total": total}
 
 
@router.get("/", dependencies=[Depends(verificar_token)])
def listar_ventas(db: Session = Depends(get_db)):
    """Lista las ventas con sus productos (items): nombre, cantidad y precio."""
    ventas = db.query(Sale).order_by(Sale.date.desc()).all()
    productos = {p.id: p.name for p in db.query(Product).all()}
 
    items_por_venta: dict[int, list] = {}
    for d in db.query(SaleDetail).all():
        items_por_venta.setdefault(d.sale_id, []).append(
            {
                "product_id": d.product_id,
                "product": productos.get(d.product_id, f"Producto #{d.product_id}"),
                "quantity": d.quantity,
                "price": d.price,
            }
        )
 
    return [
        {
            "id": v.id,
            "date": v.date,
            "total": v.total,
            "user": v.user,
            "items": items_por_venta.get(v.id, []),
        }
        for v in ventas
    ]
 
 
@router.get("/{venta_id}", dependencies=[Depends(verificar_token)])
def detalle_venta(venta_id: int, db: Session = Depends(get_db)):
    venta = db.get(Sale, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
 
    detalles = (
        db.query(SaleDetail, Product.name)
        .outerjoin(Product, Product.id == SaleDetail.product_id)
        .filter(SaleDetail.sale_id == venta_id)
        .all()
    )
    return {
        "venta": venta,
        "detalles": [
            {
                "product_id": d.product_id,
                "producto": nombre,
                "quantity": d.quantity,
                "price": d.price,
                "subtotal": round(d.quantity * d.price, 2),
            }
            for d, nombre in detalles
        ],
    }
 
