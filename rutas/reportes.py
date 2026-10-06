from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse, FileResponse

from app.dependencies import get_db
from app.models import Product
from Rutas.auth import require_role

import pandas as pd
from io import BytesIO
import tempfile

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

router = APIRouter(prefix="/reportes", tags=["Reportes"])


# ---------------------------------------------------------
# 📌 REPORTE EXCEL
# ---------------------------------------------------------
@router.get("/excel", dependencies=[Depends(require_role("admin"))])
def generar_excel(db: Session = Depends(get_db)):
    productos = db.query(Product).all()

    data = [{
        "ID": p.id,
        "SKU": p.sku,
        "Nombre": p.name,
        "Marca": p.brand,
        "Categoría": p.category,
        "Precio": p.price,
        "Stock": p.stock,
        "Activo": p.is_active
    } for p in productos]

    df = pd.DataFrame(data)

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=productos.xlsx"}
    )


# ---------------------------------------------------------
# 📌 REPORTE PDF
# ---------------------------------------------------------
@router.get("/pdf", dependencies=[Depends(require_role("admin"))])
def generar_pdf(db: Session = Depends(get_db)):
    productos = db.query(Product).all()

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp.name, pagesize=letter)

    y = 750
    c.setFont("Helvetica", 12)
    c.drawString(50, y, "Reporte de Productos")
    y -= 30

    c.setFont("Helvetica", 10)

    for p in productos:
        c.drawString(
            50,
            y,
            f"{p.id} - {p.name} - {p.brand} - {p.category} - Stock: {p.stock}"
        )
        y -= 20

        # Nueva página si se llena
        if y < 50:
            c.showPage()
            c.setFont("Arial", 10)
            y = 750

    c.save()

    return FileResponse(temp.name, filename="productos.pdf")
