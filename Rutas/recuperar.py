import os
from datetime import datetime, timedelta, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from dependencies import get_db
from models import User
from Rutas.auth import hash_password
from sqlalchemy import func

user = (
    db.query(User)
    .filter(func.lower(User.email) == data.email.strip().lower())
    .first()
)

router = APIRouter(prefix="/auth", tags=["Recuperar contraseña"])

RESET_SECRET = os.getenv("RESET_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)


def create_reset_token(email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode(
        {"sub": email, "type": "reset", "exp": exp},
        RESET_SECRET,
        algorithm="HS256",
    )


def send_email(to: str, link: str):
    """Envío por la API HTTP de Resend (funciona en Render)."""
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {os.getenv('RESEND_API_KEY')}"},
        json={
            "from": os.getenv("MAIL_FROM", "onboarding@resend.dev"),
            "to": [to],
            "subject": "Restablecer contraseña",
            "html": f"<p>Usa este enlace (válido 15 minutos):</p><p><a href='{link}'>{link}</a></p>",
        },
        timeout=10,
    )
    print("Resend respondió:", r.status_code, r.text)
    r.raise_for_status()


@router.post("/forgot-password")
def forgot_password(data: ForgotIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=data.email).first()
    print("forgot-password:", data.email, "| usuario encontrado:", bool(user))
    if user:
        token = create_reset_token(user.email)
        try:
            send_email(user.email, f"{FRONTEND_URL}/restablecer?token={token}")
        except Exception as e:
            print("Error enviando correo:", repr(e))
    # Misma respuesta exista o no el correo
    return {"message": "Si el correo existe, recibirás un enlace."}


@router.post("/reset-password")
def reset_password(data: ResetIn, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, RESET_SECRET, algorithms=["HS256"])
        if payload.get("type") != "reset":
            raise JWTError()
    except JWTError:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    user = db.query(User).filter_by(email=payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    user.password = hash_password(data.new_password)
    db.commit()
    return {"message": "Contraseña actualizada"}
