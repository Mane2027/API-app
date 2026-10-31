from typing import Optional
 
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
 
from dependencies import get_db
from models import Customer, Sale
from Rutas.auth import require_role
from Rutas.logs import registrar_log
 
router = APIRouter(prefix="/clientes", tags=["Clientes"])
 
# Quienes facturan manejan clientes; solo admin puede eliminarlos
ROLES_CLIENTES = ("admin", "vendedor")
 
 
class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    document: Optional[str] = Field(default=None, max_length=30)  # NIT o cédula
    email: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = Field(default=None, max_length=200)
 
 
class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    document: Optional[str] = Field(default=None, max_length=30)
    email: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = Field(default=None, max_length=200)
 
 
def _cliente(c: Customer) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "document": c.document,
        "email": c.email,
        "phone": c.phone,
        "address": c.address,
        "created_at": c.created_at,
    }
 
 
def _limpiar(valor: Optional[str]) -> Optional[str]:
    """Quita espacios; un texto vacío se guarda como NULL."""
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None
 
 
def _validar_documento_unico(db: Session, document: Optional[str], excluir_id: Optional[int] = None):
    if not document:
        return
    consulta = db.query(Customer).filter(Customer.document == document)
    if excluir_id is not None:
        consulta = consulta.filter(Customer.id != excluir_id)
    if consulta.first():
        raise HTTPException(status_code=400, detail=f"Ya existe un cliente con el documento {document}")
 
 
@router.post("/")
def crear_cliente(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role(*ROLES_CLIENTES)),
):
    nombre = data.name.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    documento = _limpiar(data.document)
    _validar_documento_unico(db, documento)
 
    cliente = Customer(
        name=nombre,
        document=documento,
        email=_limpiar(data.email),
        phone=_limpiar(data.phone),
        address=_limpiar(data.address),
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
 
    registrar_log(db, payload["sub"], "cliente_creado", f"Cliente ID {cliente.id}: {cliente.name}")
    return _cliente(cliente)
 
 
@router.get("/", dependencies=[Depends(require_role(*ROLES_CLIENTES))])
def listar_clientes(
    q: Optional[str] = Query(None, description="Busca por nombre o documento"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    consulta = db.query(Customer)
    if q and q.strip():
        patron = f"%{q.strip()}%"
        consulta = consulta.filter(or_(Customer.name.ilike(patron), Customer.document.ilike(patron)))
    clientes = consulta.order_by(Customer.name).offset(skip).limit(limit).all()
    return [_cliente(c) for c in clientes]
 
 
@router.get("/{cliente_id}", dependencies=[Depends(require_role(*ROLES_CLIENTES))])
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.get(Customer, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return _cliente(cliente)
 
 
@router.put("/{cliente_id}")
def actualizar_cliente(
    cliente_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role(*ROLES_CLIENTES)),
):
    cliente = db.get(Customer, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
 
    cambios = data.model_dump(exclude_unset=True)
    if "name" in cambios:
        nombre = (cambios["name"] or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
        cliente.name = nombre
    if "document" in cambios:
        documento = _limpiar(cambios["document"])
        _validar_documento_unico(db, documento, excluir_id=cliente_id)
        cliente.document = documento
    if "email" in cambios:
        cliente.email = _limpiar(cambios["email"])
    if "phone" in cambios:
        cliente.phone = _limpiar(cambios["phone"])
    if "address" in cambios:
        cliente.address = _limpiar(cambios["address"])
 
    db.commit()
    db.refresh(cliente)
 
    registrar_log(db, payload["sub"], "cliente_actualizado", f"Cliente ID {cliente.id}: {cliente.name}")
    return _cliente(cliente)
 
 
@router.delete("/{cliente_id}")
def eliminar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    cliente = db.get(Customer, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
 
    # No se elimina un cliente que ya tiene facturas: se perdería el historial
    if db.query(Sale.id).filter(Sale.customer_id == cliente_id).first():
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: el cliente tiene facturas asociadas",
        )
 
    nombre = cliente.name
    db.delete(cliente)
    db.commit()
 
    registrar_log(db, payload["sub"], "cliente_eliminado", f"Cliente ID {cliente_id}: {nombre}")
    return {"message": "Cliente eliminado correctamente"}
 
