from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AccessLog, Role
from app.permissions import ROLE_HEADER, ensure_role, resolve_role
from app.schemas import AccessLogOut

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=list[AccessLogOut])
def list_logs(db: Session = Depends(get_db), x_card_uid: str | None = ROLE_HEADER, limit: int = 200):
    _, role = resolve_role(db, x_card_uid)
    ensure_role(role, {Role.STAFF, Role.ADMIN}, "Only staff and admins can view usage logs")
    return db.query(AccessLog).order_by(AccessLog.timestamp.desc()).limit(limit).all()
