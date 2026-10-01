import smtplib
from email.mime.text import MIMEText

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "TU_CORREO@gmail.com"
SMTP_PASSWORD = "TU_PASSWORD_APP"  # contraseña de aplicación

def enviar_correo(destinatario: str, asunto: str, mensaje: str):
    msg = MIMEText(mensaje)
    msg["Subject"] = asunto
    msg["From"] = SMTP_EMAIL
    msg["To"] = destinatario

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, destinatario, msg.as_string())
