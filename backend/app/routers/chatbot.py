from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AccessLog, CardHolder, ExamEntry, Role, ScheduleEntry
from app.permissions import resolve_role
from app.schemas import ChatRequest, ChatResponse
from app.services.llm import LLMError, ask

router = APIRouter(prefix="/api/chat", tags=["chatbot"])

_DAY_NAMES_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


def _build_student_context(db: Session, holder: CardHolder) -> str:
    """Render this one card_uid's own schedule/exams as plain text for the
    chatbot's system prompt. Only ever called with the holder resolved from
    the caller's own card_uid (see resolve_role) -- never another
    student's -- so this can't leak someone else's timetable."""
    schedule = (
        db.query(ScheduleEntry)
        .filter_by(student_id=holder.id)
        .order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time)
        .all()
    )
    exams = (
        db.query(ExamEntry).filter_by(student_id=holder.id).order_by(ExamEntry.exam_date, ExamEntry.start_time).all()
    )

    lines = [f"ชื่อ: {holder.full_name} (รหัสนักศึกษา {holder.student_id or '-'})"]

    lines.append("ตารางเรียนประจำสัปดาห์:")
    if schedule:
        for entry in schedule:
            room = f"ห้อง {entry.room.room_number} ชั้น {entry.room.floor}" if entry.room else "ไม่ระบุห้อง"
            lines.append(
                f"- วัน{_DAY_NAMES_TH[entry.day_of_week]} {entry.start_time}-{entry.end_time} "
                f"วิชา {entry.course.code} {entry.course.name_th} ({room})"
            )
    else:
        lines.append("- ไม่มีตารางเรียน")

    lines.append("ตารางสอบ:")
    if exams:
        for exam in exams:
            room = f"ห้อง {exam.room.room_number}" if exam.room else "ไม่ระบุห้อง"
            exam_label = "ปลายภาค" if exam.exam_type == "final" else "กลางภาค"
            lines.append(
                f"- {exam.exam_date} {exam.start_time}-{exam.end_time} วิชา {exam.course.code} "
                f"{exam.course.name_th} ({exam_label}, {room})"
            )
    else:
        lines.append("- ไม่มีตารางสอบ")

    return "\n".join(lines)


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """Open to guests too -- the department FAQ chatbot is a self-service
    tool for anyone at the kiosk, not just CS students."""
    holder, role = resolve_role(db, payload.card_uid)

    student_context = None
    if holder is not None and role in (Role.CS_STUDENT, Role.STAFF, Role.ADMIN):
        student_context = _build_student_context(db, holder)

    try:
        reply = ask(payload.message, student_context=student_context)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db.add(
        AccessLog(
            card_uid=payload.card_uid,
            role=role.value,
            action="chat",
            detail=payload.message[:500],
            granted=True,
        )
    )
    db.commit()
    return ChatResponse(reply=reply)
