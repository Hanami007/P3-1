from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AccessLog, ExamEntry, Role, ScheduleEntry
from app.permissions import ROLE_HEADER, ensure_role, resolve_role
from app.schemas import ExamEntryOut, ScheduleEntryOut

router = APIRouter(prefix="/api/students", tags=["schedule"])


def _authorize(db: Session, student_card_uid: str, x_card_uid: str | None) -> Role:
    """The caller's identity comes ONLY from the X-Card-UID header (the card
    actually tapped at the kiosk) -- never from the path parameter, which is
    just "whose schedule is being requested" and is otherwise unauthenticated
    input."""
    holder, role = resolve_role(db, x_card_uid)
    ensure_role(
        role,
        {Role.CS_STUDENT, Role.STAFF, Role.ADMIN},
        "Only Computer Science students, staff, and admins can view schedules",
    )
    if holder is not None and holder.card_uid != student_card_uid and role not in (Role.STAFF, Role.ADMIN):
        raise HTTPException(status_code=403, detail="You may only view your own schedule")
    return role


@router.get("/{student_card_uid}/schedule", response_model=list[ScheduleEntryOut])
def get_schedule(
    student_card_uid: str,
    db: Session = Depends(get_db),
    x_card_uid: str | None = ROLE_HEADER,
):
    role = _authorize(db, student_card_uid, x_card_uid)
    entries = db.query(ScheduleEntry).join(ScheduleEntry.student).filter_by(card_uid=student_card_uid).all()
    db.add(AccessLog(card_uid=x_card_uid, role=role.value, action="schedule_view", granted=True))
    db.commit()
    return entries


@router.get("/{student_card_uid}/exams", response_model=list[ExamEntryOut])
def get_exams(
    student_card_uid: str,
    db: Session = Depends(get_db),
    x_card_uid: str | None = ROLE_HEADER,
):
    role = _authorize(db, student_card_uid, x_card_uid)
    entries = db.query(ExamEntry).join(ExamEntry.student).filter_by(card_uid=student_card_uid).all()
    db.add(AccessLog(card_uid=x_card_uid, role=role.value, action="exam_view", granted=True))
    db.commit()
    return entries
