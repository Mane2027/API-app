from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dependencies import get_db
from models import User
from jose import jwt
from passlib.context import CryptContext
import os
from datetime import datetime, timedelta

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

# Seguridad
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -----------------------------
# Esquemas Pydantic
# -----------------------------
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    role: str = "user"   # por defecto usuario normal

class UserLogin(BaseModel):
    username: str
    password: str

# -----------------------------
# Funciones auxiliares
# -----------------------------
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)

def create_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(hours=3)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# -----------------------------
# Rutas
# -----------------------------

@router.post("/registro")
def register_user(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=data.username).first():
        raise HTTPException(status_code=409, detail="Usuario ya existe")

    if db.query(User).filter_by(email=data.email).first():
        raise HTTPException(status_code=409, detail="Email ya registrado")

    hashed = hash_password(data.password)

    user = User(
        username=data.username,
        email=data.email,
        password=hashed,
        role=data.role   # ← AQUÍ VA
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Usuario registrado correctamente", "user": user.username}


@router.post("/login")
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=data.username).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = create_token({
        "sub": user.username,
        "role": user.role   # ← IMPORTANTE
    })

    return {"access_token": token, "token_type": "bearer"}
