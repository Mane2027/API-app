from pydantic import BaseModel

class PurchaseItem(BaseModel):
    product_id: int
    quantity: int
    price: float  # precio de compra

class PurchaseSchema(BaseModel):
    provider_id: int
    items: list[PurchaseItem]
