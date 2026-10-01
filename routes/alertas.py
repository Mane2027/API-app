from sqlalchemy.orm import Session
from app.models import Product, StockAlert

def generar_alerta(db: Session, product: Product):
    if product.stock == 0:
        nivel = "agotado"
        mensaje = f"El producto {product.name} está agotado."
    elif product.stock <= product.min_stock:
        nivel = "bajo"
        mensaje = f"El producto {product.name} tiene stock bajo ({product.stock})."
    else:
        return  # No genera alerta

    alerta = StockAlert(
        product_id=product.id,
        message=mensaje,
        level=nivel
    )

    db.add(alerta)
    db.commit()
