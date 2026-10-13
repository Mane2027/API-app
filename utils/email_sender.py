import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger("inventario.email")


def enviar_correo(destinatario: str | None, asunto: str, mensaje: str) -> bool:
    """Envía un correo usando variables de entorno. Nunca lanza excepciones:
    si el SMTP no está configurado o falla, solo lo registra y devuelve False."""
    servidor = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    puerto = int(os.getenv("SMTP_PORT", "587"))
    correo = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_PASSWORD")

    if not (destinatario and correo and password):
        logger.info("SMTP no configurado: se omite el correo '%s'", asunto)
        return False

    msg = MIMEText(mensaje)
    msg["Subject"] = asunto
    msg["From"] = correo
    msg["To"] = destinatario

    try:
        with smtplib.SMTP(servidor, puerto, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(correo, password)
            smtp.sendmail(correo, destinatario, msg.as_string())
        return True
    except Exception:
        logger.exception("No se pudo enviar el correo '%s'", asunto)
        return False
