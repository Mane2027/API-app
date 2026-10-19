from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
 
from dependencies import get_db
from models import InventoryMovement, Product, Provider, Purchase, PurchaseDetail
from Rutas.alertas import enviar_alertas_por_correo, generar_alerta
from Rutas.auth import require_role
from Rutas.logs import registrar_log
 
router = APIRouter(prefix="/compras", tags=["Compras"])
 
# Roles que pueden ver y registrar compras (entradas de inventario)
ROLES_COMPRAS = ("admin", "inventario")
 
 
class PurchaseItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    price: float = Field(ge=0)  # costo unitario
 
 
class PurchaseSchema(BaseModel):
    provider_id: int
    items: list[PurchaseItem] = Field(min_length=1)
 
 
@router.post("/")
def registrar_compra(
    data: PurchaseSchema,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role(*ROLES_COMPRAS)),
):
    if not db.get(Provider, data.provider_id):
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
 
    # Validar todo ANTES de escribir nada
    productos = {}
    for item in data.items:
        producto = db.get(Product, item.product_id)
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no existe")
        productos[item.product_id] = producto
 
    total = round(sum(i.price * i.quantity for i in data.items), 2)
 
    # Todo en UNA transacción: o se guarda la compra completa o no se guarda nada
    compra = Purchase(total=total, provider_id=data.provider_id, user=payload["sub"])
    db.add(compra)
    db.flush()  # obtiene compra.id sin hacer commit
 
    mensajes = []
    for item in data.items:
        producto = productos[item.product_id]
        db.add(
            PurchaseDetail(
                purchase_id=compra.id,
                product_id=producto.id,
                quantity=item.quantity,
                price=item.price,
            )
        )
 
        anterior = producto.stock
        producto.stock = anterior + item.quantity
        db.add(
            InventoryMovement(
                product_id=producto.id,
                movement_type="entrada",
                quantity=item.quantity,
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
 
    registrar_log(db, payload["sub"], "compra", f"Compra ID {compra.id}, total {total}")
    return {"message": "Compra registrada correctamente", "compra_id": compra.id, "total": total}
 
 
@router.get("/", dependencies=[Depends(require_role(*ROLES_COMPRAS))])
def listar_compras(db: Session = Depends(get_db)):
    """Lista las compras con el nombre del proveedor y sus productos (items)."""
    compras = db.query(Purchase).order_by(Purchase.date.desc()).all()
    proveedores = {p.id: p.name for p in db.query(Provider).all()}
    productos = {p.id: p.name for p in db.query(Product).all()}
 
    items_por_compra: dict[int, list] = {}
    for d in db.query(PurchaseDetail).all():
        items_por_compra.setdefault(d.purchase_id, []).append(
            {
                "product_id": d.product_id,
                "product": productos.get(d.product_id, f"Producto #{d.product_id}"),
                "quantity": d.quantity,
                "price": d.price,
            }
        )
 
    return [
        {
            "id": c.id,
            "date": c.date,
            "total": c.total,
            "user": c.user,
            "provider_id": c.provider_id,
            "provider": proveedores.get(c.provider_id, f"Proveedor #{c.provider_id}"),
            "items": items_por_compra.get(c.id, []),
        }
        for c in compras
    ]
 
 
@router.get("/{compra_id}", dependencies=[Depends(require_role(*ROLES_COMPRAS))])
def detalle_compra(compra_id: int, db: Session = Depends(get_db)):
    compra = db.get(Purchase, compra_id)
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return {"compra": compra, "detalles": compra.details}
 
