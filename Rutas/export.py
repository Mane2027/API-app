from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from dependencies import get_db
import models

router = APIRouter(prefix="/export", tags=["Export"])


# ---------- EXCEL ----------
@router.get("/ventas")
def exportar_ventas_excel(db: Session = Depends(get_db)):
    ventas = db.query(models.Sale).all()  # ajusta al nombre real de tu modelo

    wb = Workbook()
    ws = wb.active
    ws.title = "Ventas"
    ws.append(["ID", "Producto", "Cantidad", "Precio", "Total", "Fecha"])

    for v in ventas:
        ws.append([v.id, v.product_id, v.cantidad, v.precio, v.total, str(v.fecha)])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ventas.xlsx"},
    )


# ---------- PDF ----------
@router.get("/ventas/pdf")
def exportar_ventas_pdf(db: Session = Depends(get_db)):
    ventas = db.query(models.Sale).all()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Reporte de Ventas")
    pdf.setFont("Helvetica", 10)
    y -= 30

    for v in ventas:
        pdf.drawString(50, y, f"{v.id} - Producto {v.product_id} - Cant: {v.cantidad} - Total: {v.total}")
        y -= 18
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 750

    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=ventas.pdf"},
    )
