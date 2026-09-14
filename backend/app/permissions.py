"""Role-based access control.

The kiosk has no login session: possession of a physical card *is* the
credential. Every protected endpoint re-resolves the caller's role from the
card UID it was tapped with (sent as the ``X-Card-UID`` header or a query
param), so a card revoked/deactivated in the DB loses access immediately.
"""

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.models import CardHolder, Role


def resolve_role(db: Session, card_uid: str | None) -> tuple[CardHolder | None, Role]:
    if not card_uid:
        return None, Role.GUEST
    holder = db.query(CardHolder).filter(CardHolder.card_uid == card_uid).first()
    if not holder or not holder.is_active:
        return None, Role.GUEST
    return holder, holder.role


ROLE_HEADER = Header(default=None, alias="X-Card-UID")


def ensure_role(holder_role: Role, allowed: set[Role], detail: str = "Access denied for this user type"):
    if holder_role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
