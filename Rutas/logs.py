from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from dependencies import get_db
from models import AuditLog
from Rutas.auth import require_role

router = APIRouter(prefix="/logs", tags=["Logs"])


def registrar_log(db: Session, username: str, action: str, details: str):
    db.add(AuditLog(username=username, action=action, details=details))
    db.commit()


@router.get("/", dependencies=[Depends(require_role("admin"))])
def listar_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
