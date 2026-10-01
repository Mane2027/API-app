import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models import Product
from Rutas.auth import verificar_token, require_role
from io import BytesIO

router = APIRouter(prefix="/reportes", tags=["Reportes"])

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
