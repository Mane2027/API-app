from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas

from dependencies import get_db
import models

router = APIRouter(prefix="/export", tags=["Export"])


def _columnas_y_filas(db: Session):
    columnas = [c.name for c in models.Sale.__table__.columns]
    ventas = db.query(models.Sale).all()
    filas = [[str(getattr(v, c)) if getattr(v, c) is not None else "" for c in columnas]
             for v in ventas]
    return columnas, filas


# ---------- EXCEL ----------
@router.get("/ventas")
def exportar_ventas_excel(db: Session = Depends(get_db)):
    columnas, filas = _columnas_y_filas(db)

    wb = Workbook()
    ws = wb.active
    ws.title = "Ventas"
    ws.append(columnas)
    for fila in filas:
        ws.append(fila)

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
    columnas, filas = _columnas_y_filas(db)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
    ancho, alto = landscape(letter)
    y = alto - 50

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "Reporte de Ventas")
    y -= 30

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(40, y, " | ".join(columnas))
    y -= 18
    pdf.setFont("Helvetica", 9)

    for fila in filas:
        pdf.drawString(40, y, " | ".join(fila))
        y -= 16
        if y < 40:
            pdf.showPage()
            pdf.setFont("Helvetica", 9)
            y = alto - 40

    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=ventas.pdf"},
    )
