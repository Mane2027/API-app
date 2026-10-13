import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from dependencies import get_db
from models import Product, StockAlert
from Rutas.auth import verificar_token
from utils.email_sender import enviar_correo

router = APIRouter(prefix="/alertas", tags=["Alertas"])


def generar_alerta(db: Session, product: Product) -> str | None:
    """Agrega una alerta si el stock está bajo o agotado y devuelve el mensaje.
    NO hace commit (lo hace quien llama, para que todo sea una sola transacción)
    ni envía correo (ver enviar_alertas_por_correo)."""
    if product.stock == 0:
        nivel = "agotado"
        mensaje = f"⚠️ El producto '{product.name}' está AGOTADO."
    elif product.stock <= product.min_stock:
        nivel = "bajo"
        mensaje = f"⚠️ El producto '{product.name}' tiene stock bajo ({product.stock})."
    else:
        return None

    db.add(StockAlert(product_id=product.id, message=mensaje, level=nivel))
    return mensaje


def enviar_alertas_por_correo(mensajes: list[str]):
    """Se ejecuta en segundo plano DESPUÉS de responder; un solo correo con todo."""
    if mensajes:
        enviar_correo(
            os.getenv("ADMIN_EMAIL"),
            "Alerta de inventario",
            "\n".join(mensajes),
        )


@router.get("/", dependencies=[Depends(verificar_token)])
def obtener_alertas(db: Session = Depends(get_db)):
    return db.query(StockAlert).order_by(StockAlert.timestamp.desc()).all()
