from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models import Product, StockAlert
from app.utils.email_sender import enviar_correo
from Rutas.auth import verificar_token, require_role

router = APIRouter(prefix="/alertas", tags=["Alertas"])

ADMIN_EMAIL = "TU_CORREO_ADMIN@gmail.com"


# ---------------------------------------------------------
# 📌 FUNCIÓN AUTOMÁTICA PARA GENERAR ALERTAS
# ---------------------------------------------------------
def generar_alerta(db: Session, product: Product):
    # Determinar nivel de alerta
    if product.stock == 0:
        nivel = "agotado"
        mensaje = f"⚠️ El producto '{product.name}' está AGOTADO."
    elif product.stock <= product.min_stock:
        nivel = "bajo"
        mensaje = f"⚠️ El producto '{product.name}' tiene stock bajo ({product.stock})."
    else:
        return  # No genera alerta

    # Guardar alerta en la base de datos
    alerta = StockAlert(
        product_id=product.id,
        message=mensaje,
        level=nivel
    )
    db.add(alerta)
    db.commit()

    # Enviar correo automático
    enviar_correo(
        ADMIN_EMAIL,
        f"Alerta de inventario: {product.name}",
        mensaje
    )


# ---------------------------------------------------------
# 📌 ENDPOINT PARA VER TODAS LAS ALERTAS
# ---------------------------------------------------------
@router.get("/", dependencies=[Depends(verificar_token)])
def obtener_alertas(db: Session = Depends(get_db)):
    return db.query(StockAlert).order_by(StockAlert.timestamp.desc()).all()
