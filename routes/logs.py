from app.models import AuditLog
from sqlalchemy.orm import Session

def registrar_log(db: Session, username: str, action: str, details: str):
    log = AuditLog(username=username, action=action, details=details)
    db.add(log)
    db.commit()
