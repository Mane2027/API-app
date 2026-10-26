from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from dependencies import get_db
from models import User
from Rutas.auth import (
    create_token, hash_password, require_role, verificar_token, verify_password,
)
from Rutas.logs import registrar_log
ROLES_VALIDOS = ("admin", "inventario", "vendedor", "user")


router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Literal["admin", "inventario", "vendedor", "user"]




class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)
    role: Literal["admin", "inventario", "vendedor", "user"]


def _publico(u: User) -> dict:
    """Nunca devolver el hash de la contraseña."""
    return {"id": u.id, "username": u.username, "email": u.email, "role": u.role}


def _autenticar(db: Session, username: str, password: str) -> dict:
    user = db.query(User).filter_by(username=username).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = create_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
@router.post("/login")
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    """Login con JSON (el que usa el frontend)."""
    return _autenticar(db, data.username, data.password)


@router.post("/token", include_in_schema=False)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login con formulario: lo usa el botón 'Authorize' de /docs."""
    return _autenticar(db, form.username, form.password)


# ---------------------------------------------------------
# REGISTRO — solo un administrador puede crear usuarios
# (antes cualquiera podía registrarse con role="admin")
# ---------------------------------------------------------
@router.post("/registro")
def register_user(
    data: UserRegister,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    if db.query(User).filter_by(username=data.username).first():
        raise HTTPException(status_code=409, detail="Usuario ya existe")
    if db.query(User).filter_by(email=data.email).first():
        raise HTTPException(status_code=409, detail="Email ya registrado")

    user = User(
        username=data.username,
        email=data.email,
        password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    registrar_log(db, payload["sub"], "crear_usuario", f"Usuario: {user.username} ({user.role})")
    return {"message": "Usuario registrado correctamente", "user": user.username}


# ---------------------------------------------------------
# CONSULTA Y ADMINISTRACIÓN
# ---------------------------------------------------------
@router.get("/me")
def mi_perfil(payload: dict = Depends(verificar_token), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _publico(user)


@router.get("/", dependencies=[Depends(require_role("admin"))])
def listar_usuarios(db: Session = Depends(get_db)):
    return [_publico(u) for u in db.query(User).order_by(User.id).all()]


@router.get("/{user_id}", dependencies=[Depends(require_role("admin"))])
def obtener_usuario(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _publico(user)


@router.put("/{user_id}")
def actualizar_usuario(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    cambios = data.model_dump(exclude_unset=True)
    if "email" in cambios and cambios["email"] != user.email:
        if db.query(User).filter_by(email=cambios["email"]).first():
            raise HTTPException(status_code=409, detail="Email ya registrado")
        user.email = cambios["email"]
    if cambios.get("password"):
        user.password = hash_password(cambios["password"])
    if cambios.get("role"):
        user.role = cambios["role"]

    db.commit()
    registrar_log(db, payload["sub"], "actualizar_usuario", f"ID: {user_id}")
    return _publico(user)


@router.delete("/{user_id}")
def eliminar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_role("admin")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.username == payload["sub"]:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario")

    db.delete(user)
    db.commit()
    registrar_log(db, payload["sub"], "eliminar_usuario", f"ID: {user_id}")
    return {"message": "Usuario eliminado correctamente"}
