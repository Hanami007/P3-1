from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AccessLog, Role
from app.permissions import resolve_role
from app.schemas import CardScanRequest, CardScanResponse

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.post("/scan", response_model=CardScanResponse)
def scan_card(payload: CardScanRequest, db: Session = Depends(get_db)):
    """Called when the RFID/NFC reader picks up a card tap.

    Unknown cards are treated as guests rather than rejected outright, since
    the kiosk still offers building/room lookup and the general chatbot to
    anyone (requirement: non-CS students self-serve without logging in).
    """
    holder, role = resolve_role(db, payload.card_uid)

    if holder is None:
        message = "ไม่พบข้อมูลบัตรนี้ในระบบ ใช้งานในโหมดผู้เยี่ยมชมได้"
    elif role == Role.CS_STUDENT:
        message = f"ยินดีต้อนรับ {holder.full_name}"
    else:
        message = f"ยินดีต้อนรับ {holder.full_name} ({role.value})"

    db.add(
        AccessLog(
            card_uid=payload.card_uid,
            card_holder_id=holder.id if holder else None,
            role=role.value,
            action="card_scan",
            detail=message,
            granted=True,
        )
    )
    db.commit()

    return CardScanResponse(recognized=holder is not None, holder=holder, role=role, message=message)
