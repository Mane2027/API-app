import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    # Sin clave fija los tokens dejan de valer en cada reinicio: úsala siempre en producción.
    SECRET_KEY = secrets.token_urlsafe(32)
    warnings.warn("JWT_SECRET_KEY no está definida; se generó una clave temporal.")

ALGORITHM = "HS256"
TOKEN_HORAS = int(os.getenv("TOKEN_EXPIRE_HOURS", "3"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/usuarios/token")


# ---------- Contraseñas (bcrypt directo; compatible con hashes de passlib) ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


# ---------- Tokens ----------
def create_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HORAS)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


def require_role(*roles: str):
    """Dependencia que exige uno de los roles y devuelve el payload del token.
    Uso: payload: dict = Depends(require_role("admin"))"""

    def role_checker(payload: dict = Depends(verificar_token)) -> dict:
        if payload.get("role") not in roles:
            raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
        return payload

    return role_checker
