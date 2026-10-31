from collections import defaultdict
 
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
 
from dependencies import get_db
from models import AppSetting, Customer, InventoryMovement, Product, Sale, SaleDetail
from Rutas.alertas import enviar_alertas_por_correo, generar_alerta
from Rutas.auth import require_role
from Rutas.logs import registrar_log
 
router = APIRouter(prefix="/ventas", tags=["Ventas"])
 
# Roles que pueden registrar ventas
ROLES_VENTAS = ("admin", "vendedor")
# Roles que pueden consultarlas (inventario solo lee)
ROLES_CONSULTA = ("admin", "vendedor", "inventario")
 
 
class SaleItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
 
 
class SaleSchema(BaseModel):
    items: list[SaleItem] = Field(min_length=1)
 
 
def crear_venta(
    db: Session,
    items: list[SaleItem],
    usuario: str,
    background: BackgroundTasks,
    customer_id: int | None = None,
    facturar: bool = False,
) -> Sale:
    """
    Lógica común de venta y factura: valida stock, calcula IVA, descuenta
    inventario y registra movimientos en una sola transacción.
    Si facturar=True asigna número consecutivo de factura.
    """
    # Si el mismo producto viene dos veces, se suman las cantidades
    cantidades: dict[int, int] = defaultdict(int)
    for item in items:
        cantidades[item.product_id] += item.quantity
 
    if customer_id is not None and not db.get(Customer, customer_id):
        raise HTTPException(status_code=404, detail=f"Cliente {customer_id} no existe")
 
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
 
    # IVA: solo se aplica si el negocio está marcado como responsable de IVA
    config = db.query(AppSetting).first()
    aplica_iva = bool(config and config.vat_responsible)
 
    subtotal = 0.0
    impuestos = 0.0
    tasas: dict[int, float] = {}
    for pid, qty in cantidades.items():
        producto = productos[pid]
        tasa = (producto.tax_rate or 0) if aplica_iva else 0
        linea = round(producto.price * qty, 2)
        subtotal += linea
        impuestos += round(linea * tasa / 100, 2)
        tasas[pid] = tasa
    subtotal = round(subtotal, 2)
    impuestos = round(impuestos, 2)
    total = round(subtotal + impuestos, 2)
 
    venta = Sale(
        total=total,
        subtotal=subtotal,
        tax_total=impuestos,
        user=usuario,
        customer_id=customer_id,
        status="emitida",
    )
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
 
        db.add(
            SaleDetail(
                sale_id=venta.id,
                product_id=pid,
                quantity=qty,
                price=producto.price,
                tax_rate=tasas[pid],
            )
        )
        db.add(
            InventoryMovement(
                product_id=pid,
                movement_type="salida",
                quantity=qty,
                previous_stock=anterior,
                new_stock=producto.stock,
                performed_by=usuario,
            )
        )
        mensaje = generar_alerta(db, producto)
        if mensaje:
            mensajes.append(mensaje)
 
    # El número se pide al final, cuando ya se descontó todo el stock,
    # para no gastar consecutivos en facturas que fallan por falta de stock
    if facturar:
        venta.invoice_number = db.execute(text("SELECT nextval('invoice_number_seq')")).scalar()
 
    db.commit()
    background.add_task(enviar_alertas_por_correo, mensajes)
    return venta
 
 
@router.post("/")
def registrar_venta(
    data: SaleSchema,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role(*ROLES_VENTAS)),
):
    venta = crear_venta(db, data.items, payload["sub"], background)
    registrar_log(db, payload["sub"], "venta", f"Venta ID {venta.id}, total {venta.total}")
    return {"message": "Venta registrada correctamente", "venta_id": venta.id, "total": venta.total}
 
 
@router.get("/", dependencies=[Depends(require_role(*ROLES_CONSULTA))])
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
            "invoice_number": v.invoice_number,
            "status": v.status,
            "items": items_por_venta.get(v.id, []),
        }
        for v in ventas
    ]
 
 
@router.get("/{venta_id}", dependencies=[Depends(require_role(*ROLES_CONSULTA))])
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
 
  
