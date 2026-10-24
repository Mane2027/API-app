from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook

from dependencies import get_db
import models

router = APIRouter(prefix="/export", tags=["Export"])

@router.get("/ventas")
def exportar_ventas_excel(db: Session = Depends(get_db)):
    ventas = db.query(models.Sale).all()  # ajusta al nombre real de tu modelo

    wb = Workbook()
    ws = wb.active
    ws.title = "Ventas"
    ws.append(["ID", "Producto", "Cantidad", "Precio", "Total", "Fecha"])  # ajusta columnas

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
