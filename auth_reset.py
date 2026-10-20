import os, smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

# Ajusta estos imports a los nombres reales de tu proyecto
from database import get_db
from models import User
from auth import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_SECRET = os.getenv("RESET_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str


def create_reset_token(email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode({"sub": email, "type": "reset", "exp": exp}, RESET_SECRET, algorithm="HS256")


def send_email(to: str, link: str):
    msg = EmailMessage()
    msg["Subject"] = "Restablecer contraseña"
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = to
    msg.set_content(f"Usa este enlace (válido 15 min):\n{link}")
    with smtplib.SMTP_SSL(os.getenv("SMTP_HOST"), 465) as s:
        s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        s.send_message(msg)


@router.post("/forgot-password")
def forgot_password(data: ForgotIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        token = create_reset_token(user.email)
        send_email(user.email, f"{FRONTEND_URL}/restablecer?token={token}")
    return {"message": "Si el correo existe, recibirás un enlace."}


@router.post("/reset-password")
def reset_password(data: ResetIn, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, RESET_SECRET, algorithms=["HS256"])
        if payload.get("type") != "reset":
            raise JWTError()
    except JWTError:
        raise HTTPException(400, "Token inválido o expirado")
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(400, "Token inválido o expirado")
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Contraseña actualizada"}
