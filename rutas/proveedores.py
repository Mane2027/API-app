from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Provider
from Rutas.auth import verificar_token, require_role
from Rutas.logs import registrar_log

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


# ---------------------------------------------------------
# 📌 CREAR PROVEEDOR (ADMIN)
# ---------------------------------------------------------
@router.post("/", dependencies=[Depends(require_role("admin"))])
def crear_proveedor(data: ProviderSchema, db: Session = Depends(get_db)):
    payload = verificar_token()

    proveedor = Provider(**data.dict())
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)

    registrar_log(db, payload["sub"], "crear_proveedor", f"Proveedor: {proveedor.name}")

    return proveedor


# ---------------------------------------------------------
# 📌 LISTAR PROVEEDORES (Cualquier usuario autenticado)
# ---------------------------------------------------------
@router.get("/", dependencies=[Depends(verificar_token)])
def listar_proveedores(db: Session = Depends(get_db)):
    return db.query(Provider).all()


# ---------------------------------------------------------
# 📌 OBTENER PROVEEDOR POR ID
# ---------------------------------------------------------
@router.get("/{provider_id}", dependencies=[Depends(verificar_token)])
def obtener_proveedor(provider_id: int, db: Session = Depends(get_db)):
    proveedor = db.query(Provider).get(provider_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


# ---------------------------------------------------------
# 📌 ACTUALIZAR PROVEEDOR (ADMIN)
# ---------------------------------------------------------
@router.put("/{provider_id}", dependencies=[Depends(require_role("admin"))])
def actualizar_proveedor(provider_id: int, data: ProviderSchema, db: Session = Depends(get_db)):
    payload = verificar_token()

    proveedor = db.query(Provider).get(provider_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(proveedor, key, value)

    db.commit()
    db.refresh(proveedor)

    registrar_log(db, payload["sub"], "actualizar_proveedor", f"Proveedor ID: {provider_id}")

    return proveedor


# ---------------------------------------------------------
# 📌 ELIMINAR PROVEEDOR (ADMIN)
# ---------------------------------------------------------
@router.delete("/{provider_id}", dependencies=[Depends(require_role("admin"))])
def eliminar_proveedor(provider_id: int, db: Session = Depends(get_db)):
    payload = verificar_token()

    proveedor = db.query(Provider).get(provider_id)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    db.delete(proveedor)
    db.commit()

    registrar_log(db, payload["sub"], "eliminar_proveedor", f"Proveedor ID: {provider_id}")

    return {"message": "Proveedor eliminado correctamente"}
