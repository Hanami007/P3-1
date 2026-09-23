from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AccessLog, CardHolder, ExamEntry, Role, ScheduleEntry
from app.permissions import resolve_role
from app.schemas import ChatRequest, ChatResponse
from app.services.live_status import calculate_student_live_status
from app.services.llm import LLMError, ask

router = APIRouter(prefix="/api/chat", tags=["chatbot"])

_DAY_NAMES_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


def _build_student_context(db: Session, holder: CardHolder) -> str:
    """Render this one card_uid's own schedule/exams as plain text for the
    chatbot's system prompt. Only ever called with the holder resolved from
    the caller's own card_uid (see resolve_role) -- never another
    student's -- so this can't leak someone else's timetable."""
    live = calculate_student_live_status(db, holder)

    schedule = (
        db.query(ScheduleEntry)
        .filter_by(student_id=holder.id)
        .order_by(ScheduleEntry.day_of_week, ScheduleEntry.start_time)
        .all()
    )
    exams = (
        db.query(ExamEntry).filter_by(student_id=holder.id).order_by(ExamEntry.exam_date, ExamEntry.start_time).all()
    )

    lines = [
        f"ชื่อ: {holder.full_name} (รหัสนักศึกษา {holder.student_id or '-'})",
        f"ข้อมูลสถานะ ณ ขณะนี้ (เวลา {live.get('current_time')} วัน{live.get('day_name_th')}): {live.get('message')}",
    ]
    if live.get("current_class"):
        c = live["current_class"]
        lines.append(f"- กำลังเรียนวิชา: {c['course_code']} {c['course_name']} ({c['start_time']}-{c['end_time']}) {c['room']}")
    if live.get("next_class"):
        n = live["next_class"]
        lines.append(f"- วิชาถัดไป: {n['course_code']} {n['course_name']} ({n['start_time']}-{n['end_time']}) {n['room']}")
    if live.get("exam_today"):
        ex = live["exam_today"]
        lines.append(f"- วันนี้มีสอบ: {ex['course_code']} {ex['course_name']} ({ex['start_time']}-{ex['end_time']}) {ex['room']}")

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
        reply = f"ขออภัยครับ ขณะนี้ระบบ AI เชื่อมต่อไม่สำเร็จ: {exc}"
    except Exception:
        reply = "ขออภัยครับ ขณะนี้ระบบ AI ประสบปัญหาการเชื่อมต่อชั่วคราว กรุณาลองใหม่อีกครั้ง หรือติดต่อห้องธุรการสาขา CS-A ชั้น 2 ครับ"

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
