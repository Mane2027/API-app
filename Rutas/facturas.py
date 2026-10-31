from datetime import date, timedelta
 
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
 
from dependencies import get_db
from models import Customer, InventoryMovement, Product, Sale, SaleDetail
from Rutas.auth import require_role
from Rutas.logs import registrar_log
from Rutas.ventas import ROLES_CONSULTA, ROLES_VENTAS, SaleSchema, crear_venta
 
router = APIRouter(prefix="/facturas", tags=["Facturas"])
 
 
class InvoiceSchema(SaleSchema):
    customer_id: int | None = None  # sin cliente = consumidor final
 
 
@router.post("/")
def crear_factura(
    data: InvoiceSchema,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role(*ROLES_VENTAS)),
):
    venta = crear_venta(
        db,
        data.items,
        payload["sub"],
        background,
        customer_id=data.customer_id,
        facturar=True,
    )
    registrar_log(
        db,
        payload["sub"],
        "factura",
        f"Factura {venta.invoice_number} (venta ID {venta.id}), total {venta.total}",
    )
    return {
        "message": "Factura emitida correctamente",
        "factura_id": venta.id,
        "numero": venta.invoice_number,
        "subtotal": venta.subtotal,
        "impuestos": venta.tax_total,
        "total": venta.total,
    }
 
 
@router.get("/", dependencies=[Depends(require_role(*ROLES_CONSULTA))])
def listar_facturas(
    desde: date | None = None,
    hasta: date | None = None,
    customer_id: int | None = None,
    status: str | None = None,  # emitida / anulada
    db: Session = Depends(get_db),
):
    q = (
        db.query(Sale, Customer.name)
        .outerjoin(Customer, Customer.id == Sale.customer_id)
        .filter(Sale.invoice_number.isnot(None))
    )
    if desde:
        q = q.filter(Sale.date >= desde)
    if hasta:
        q = q.filter(Sale.date < hasta + timedelta(days=1))
    if customer_id:
        q = q.filter(Sale.customer_id == customer_id)
    if status:
        q = q.filter(Sale.status == status)
 
    filas = q.order_by(Sale.invoice_number.desc()).all()
    return [
        {
            "id": v.id,
            "numero": v.invoice_number,
            "fecha": v.date,
            "cliente": nombre or "Consumidor final",
            "subtotal": v.subtotal,
            "impuestos": v.tax_total,
            "total": v.total,
            "estado": v.status,
            "usuario": v.user,
        }
        for v, nombre in filas
    ]
 
 
@router.get("/{factura_id}", dependencies=[Depends(require_role(*ROLES_CONSULTA))])
def detalle_factura(factura_id: int, db: Session = Depends(get_db)):
    venta = db.get(Sale, factura_id)
    if not venta or venta.invoice_number is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
 
    detalles = (
        db.query(SaleDetail, Product.name)
        .outerjoin(Product, Product.id == SaleDetail.product_id)
        .filter(SaleDetail.sale_id == factura_id)
        .all()
    )
    cliente = db.get(Customer, venta.customer_id) if venta.customer_id else None
 
    return {
        "id": venta.id,
        "numero": venta.invoice_number,
        "fecha": venta.date,
        "estado": venta.status,
        "usuario": venta.user,
        "cliente": (
            {
                "id": cliente.id,
                "nombre": cliente.name,
                "documento": cliente.document,
                "correo": cliente.email,
                "telefono": cliente.phone,
                "direccion": cliente.address,
            }
            if cliente
            else None
        ),
        "subtotal": venta.subtotal,
        "impuestos": venta.tax_total,
        "total": venta.total,
        "detalles": [
            {
                "product_id": d.product_id,
                "producto": nombre,
                "cantidad": d.quantity,
                "precio_unitario": d.price,
                "iva_porcentaje": d.tax_rate or 0,
                "subtotal": round(d.quantity * d.price, 2),
                "iva": round(d.quantity * d.price * (d.tax_rate or 0) / 100, 2),
            }
            for d, nombre in detalles
        ],
    }
 
 
@router.post("/{factura_id}/anular")
def anular_factura(
    factura_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    # Bloquea la fila para que dos anulaciones simultáneas no devuelvan el stock dos veces
    venta = db.query(Sale).filter(Sale.id == factura_id).with_for_update().first()
    if not venta or venta.invoice_number is None:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if venta.status == "anulada":
        raise HTTPException(status_code=400, detail="La factura ya está anulada")
 
    detalles = db.query(SaleDetail).filter(SaleDetail.sale_id == factura_id).all()
    for d in detalles:
        producto = db.get(Product, d.product_id)
        if not producto:
            continue
        anterior = producto.stock
        db.query(Product).filter(Product.id == d.product_id).update(
            {Product.stock: Product.stock + d.quantity}, synchronize_session=False
        )
        db.refresh(producto)
        db.add(
            InventoryMovement(
                product_id=d.product_id,
                movement_type="entrada",
                quantity=d.quantity,
                previous_stock=anterior,
                new_stock=producto.stock,
                performed_by=payload["sub"],
            )
        )
 
    venta.status = "anulada"
    numero = venta.invoice_number
    db.commit()
 
    registrar_log(db, payload["sub"], "anular_factura", f"Factura {numero} anulada (venta ID {factura_id})")
    return {"message": "Factura anulada y stock devuelto", "numero": numero}
 
