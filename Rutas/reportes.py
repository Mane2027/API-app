rom datetime import date
from io import BytesIO
 
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import func
from sqlalchemy.orm import Session
 
from dependencies import get_db
from models import (
    Product, Provider, Purchase, PurchaseDetail, Sale, SaleDetail,
)
from Rutas.auth import require_role
 
router = APIRouter(
    prefix="/reportes", tags=["Reportes"], dependencies=[Depends(require_role("admin"))]
)
 
 
def _compra(c: Purchase) -> dict:
    return {"id": c.id, "date": c.date, "total": c.total, "provider_id": c.provider_id, "user": c.user}
 
 
def _venta(v: Sale) -> dict:
    return {"id": v.id, "date": v.date, "total": v.total, "user": v.user}
 
 
# ---------------------------------------------------------
# EXCEL / PDF DE PRODUCTOS
# ---------------------------------------------------------
@router.get("/excel")
def generar_excel(db: Session = Depends(get_db)):
    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"
    ws.append(["ID", "SKU", "Nombre", "Marca", "Categoría", "Precio", "Stock", "Activo"])
    for p in db.query(Product).order_by(Product.id).all():
        ws.append([p.id, p.sku, p.name, p.brand, p.category, p.price, p.stock, p.is_active])
 
    salida = BytesIO()
    wb.save(salida)
    salida.seek(0)
    return StreamingResponse(
        salida,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=productos.xlsx"},
    )
 
 
@router.get("/pdf")
def generar_pdf(db: Session = Depends(get_db)):
    salida = BytesIO()
    c = canvas.Canvas(salida, pagesize=letter)
 
    def encabezado():
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 750, "Reporte de Productos")
        c.setFont("Helvetica", 10)
 
    encabezado()
    y = 720
    for p in db.query(Product).order_by(Product.id).all():
        c.drawString(50, y, f"{p.id} - {p.name} - {p.brand} - {p.category} - Stock: {p.stock}"[:110])
        y -= 18
        if y < 50:
            c.showPage()
            encabezado()
            y = 720
    c.save()
    salida.seek(0)
    return StreamingResponse(
        salida,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=productos.pdf"},
    )
 
 
# ---------------------------------------------------------
# COMPRAS
# ---------------------------------------------------------
@router.get("/compras/proveedor/{provider_id}")
def compras_por_proveedor(provider_id: int, db: Session = Depends(get_db)):
    proveedor = db.get(Provider, provider_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
 
    compras = db.query(Purchase).filter(Purchase.provider_id == provider_id).all()
    productos = (
        db.query(
            Product.name,
            func.sum(PurchaseDetail.quantity).label("cantidad"),
            func.sum(PurchaseDetail.quantity * PurchaseDetail.price).label("subtotal"),
        )
        .join(PurchaseDetail, PurchaseDetail.product_id == Product.id)
        .join(Purchase, Purchase.id == PurchaseDetail.purchase_id)
        .filter(Purchase.provider_id == provider_id)
        .group_by(Product.name)
        .all()
    )
    return {
        "proveedor": proveedor.name,
        "total_compras": len(compras),
        "total_invertido": sum(c.total for c in compras),
        "productos": [
            {"nombre": p.name, "cantidad_comprada": p.cantidad, "subtotal": p.subtotal}
            for p in productos
        ],
        "compras": [_compra(c) for c in compras],
    }
 
 
@router.get("/compras/producto/{product_id}")
def compras_por_producto(product_id: int, db: Session = Depends(get_db)):
    producto = db.get(Product, product_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
 
    detalles = (
        db.query(PurchaseDetail.quantity, PurchaseDetail.price, Purchase.date)
        .join(Purchase, Purchase.id == PurchaseDetail.purchase_id)
        .filter(PurchaseDetail.product_id == product_id)
        .all()
    )
    return {
        "producto": producto.name,
        "total_cantidad": sum(d.quantity for d in detalles),
        "total_invertido": sum(d.quantity * d.price for d in detalles),
        "compras": [{"quantity": d.quantity, "price": d.price, "date": d.date} for d in detalles],
    }
 
 
@router.get("/compras/fecha")
def compras_por_fecha(fecha: date, db: Session = Depends(get_db)):
    """fecha en formato YYYY-MM-DD (si es inválida responde 422, antes era error 500)."""
    compras = db.query(Purchase).filter(func.date(Purchase.date) == fecha).all()
    return {
        "fecha": fecha,
        "total_compras": len(compras),
        "total_invertido": sum(c.total for c in compras),
        "compras": [_compra(c) for c in compras],
    }
 
 
@router.get("/compras/global")
def compras_global(db: Session = Depends(get_db)):
    compras = db.query(Purchase).all()
    return {
        "total_compras": len(compras),
        "total_invertido": sum(c.total for c in compras),
        "compras": [_compra(c) for c in compras],
    }
 
 
# ---------------------------------------------------------
# VENTAS
# ---------------------------------------------------------
@router.get("/ventas/fecha")
def ventas_por_fecha(fecha: date, db: Session = Depends(get_db)):
    ventas = db.query(Sale).filter(func.date(Sale.date) == fecha).all()
    return {
        "fecha": fecha,
        "total_ventas": len(ventas),
        "total_generado": sum(v.total for v in ventas),
        "ventas": [_venta(v) for v in ventas],
    }
 
 
@router.get("/ventas/producto/{product_id}")
def ventas_por_producto(product_id: int, db: Session = Depends(get_db)):
    producto = db.get(Product, product_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
 
    detalles = (
        db.query(SaleDetail.quantity, SaleDetail.price, Sale.date)
        .join(Sale, Sale.id == SaleDetail.sale_id)
        .filter(SaleDetail.product_id == product_id)
        .all()
    )
    return {
        "producto": producto.name,
        "total_cantidad": sum(d.quantity for d in detalles),
        "total_generado": sum(d.quantity * d.price for d in detalles),
        "ventas": [{"quantity": d.quantity, "price": d.price, "date": d.date} for d in detalles],
    }
 
 
@router.get("/ventas/global")
def ventas_global(db: Session = Depends(get_db)):
    ventas = db.query(Sale).all()
    return {
        "total_ventas": len(ventas),
        "total_generado": sum(v.total for v in ventas),
        "ventas": [_venta(v) for v in ventas],
    }
 
