from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from dependencies import get_db
from models import Provider, Purchase
from Rutas.auth import require_role, verificar_token
from Rutas.logs import registrar_log

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


class ProviderSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    contact_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=200)


@router.post("/")
def crear_proveedor(
    data: ProviderSchema,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    proveedor = Provider(**data.model_dump())
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)

    registrar_log(db, payload["sub"], "crear_proveedor", f"Proveedor: {proveedor.name}")
    return proveedor


@router.get("/", dependencies=[Depends(verificar_token)])
def listar_proveedores(db: Session = Depends(get_db)):
    return db.query(Provider).order_by(Provider.id).all()


@router.get("/{provider_id}", dependencies=[Depends(verificar_token)])
def obtener_proveedor(provider_id: int, db: Session = Depends(get_db)):
    proveedor = db.get(Provider, provider_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


@router.put("/{provider_id}")
def actualizar_proveedor(
    provider_id: int,
    data: ProviderSchema,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    proveedor = db.get(Provider, provider_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    for key, value in data.model_dump().items():
        setattr(proveedor, key, value)

    db.commit()
    db.refresh(proveedor)

    registrar_log(db, payload["sub"], "actualizar_proveedor", f"Proveedor ID: {provider_id}")
    return proveedor


@router.delete("/{provider_id}")
def eliminar_proveedor(
    provider_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    proveedor = db.get(Provider, provider_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    if db.query(Purchase).filter_by(provider_id=provider_id).first():
        raise HTTPException(
            status_code=409, detail="El proveedor tiene compras registradas y no se puede eliminar"
        )

    db.delete(proveedor)
    db.commit()

    registrar_log(db, payload["sub"], "eliminar_proveedor", f"Proveedor ID: {provider_id}")
    return {"message": "Proveedor eliminado correctamente"}

