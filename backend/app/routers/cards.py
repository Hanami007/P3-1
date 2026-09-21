from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AccessLog, Role
from app.permissions import resolve_role
from app.schemas import CardScanRequest, CardScanResponse
from app.services.live_status import calculate_student_live_status

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.post("/scan", response_model=CardScanResponse)
def scan_card(payload: CardScanRequest, db: Session = Depends(get_db)):
    """Called when the RFID/NFC reader picks up a card tap or face recognition triggers.

    Unknown cards are treated as guests rather than rejected outright, since
    the kiosk still offers building/room lookup and the general chatbot to
    anyone.
    """
    holder, role = resolve_role(db, payload.card_uid)

    live_status = None
    smart_greeting = None

    if holder is None:
        message = "ไม่พบข้อมูลบัตรนี้ในระบบ ใช้งานในโหมดผู้เยี่ยมชมได้"
        smart_greeting = "สวัสดีค่ะ ไม่พบข้อมูลบัตรในระบบ คุณสามารถสอบถามข้อมูลอาคาร สถานที่ หรือข้อมูลทั่วไปของสาขาได้เลยค่ะ"
    elif role == Role.CS_STUDENT:
        live_status_dict = calculate_student_live_status(db, holder)
        live_status = live_status_dict
        message = live_status_dict["message"]
        smart_greeting = live_status_dict["smart_greeting"]
    else:
        message = f"ยินดีต้อนรับ {holder.full_name} ({role.value})"
        smart_greeting = f"สวัสดีครับคุณ {holder.full_name} มีอะไรให้ระบบคีออสก์ช่วยเหลือไหมครับ"

    noise_info = []
    if payload.ambient_noise_db is not None:
        noise_info.append(f"ambient={payload.ambient_noise_db:.1f}dB")
    if payload.peak_noise_db is not None:
        noise_info.append(f"peak={payload.peak_noise_db:.1f}dB")
        # If peak noise was very high during scan, add a gentle note to the spoken greeting
        if payload.peak_noise_db > 75.0 and smart_greeting:
            smart_greeting += " (ตรวจพบเสียงรบกวนรอบข้างค่อนข้างดัง แนะนำให้พูดใกล้ไมโครโฟนนะครับ)"

    detail_str = message
    if noise_info:
        detail_str += f" | {', '.join(noise_info)}"

    db.add(
        AccessLog(
            card_uid=payload.card_uid,
            card_holder_id=holder.id if holder else None,
            role=role.value,
            action="card_scan",
            detail=detail_str,
            granted=True,
        )
    )
    db.commit()

    return CardScanResponse(
        recognized=holder is not None,
        holder=holder,
        role=role,
        message=message,
        smart_greeting=smart_greeting,
        live_status=live_status,
    )
