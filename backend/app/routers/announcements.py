from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Announcement
from app.permissions import ROLE_HEADER, resolve_role
from app.schemas import AnnouncementOut

router = APIRouter(prefix="/api/announcements", tags=["announcements"])


@router.get("", response_model=list[AnnouncementOut])
def list_announcements(db: Session = Depends(get_db), x_card_uid: str | None = ROLE_HEADER):
    _, role = resolve_role(db, x_card_uid)
    query = db.query(Announcement)
    if role.value not in ("staff", "admin"):
        query = query.filter(Announcement.audience.in_(["all", role.value]))
    return query.order_by(Announcement.created_at.desc()).all()
