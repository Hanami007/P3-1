from datetime import datetime, time
from sqlalchemy.orm import Session

from app.models import CardHolder, ExamEntry, Role, ScheduleEntry

_DAY_NAMES_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


def _parse_time_str(t_str: str) -> time:
    parts = t_str.split(":")
    return time(int(parts[0]), int(parts[1]))


def calculate_student_live_status(
    db: Session,
    holder: CardHolder,
    current_dt: datetime | None = None,
) -> dict:
    """Calculates real-time schedule context for a student.

    Determines:
    - Current day and time
    - Today's exam if any
    - Ongoing class (and whether the student is late / class is in progress)
    - Upcoming class (if starting soon or later today)
    - All classes completed today or no classes today
    - Formats an intelligent, proactive smart greeting for voice/chat.
    """
    if holder.role not in (Role.CS_STUDENT, Role.STAFF, Role.ADMIN):
        return {
            "has_schedule": False,
            "status": "not_applicable",
            "message": f"ยินดีต้อนรับคุณ {holder.full_name}",
            "smart_greeting": f"สวัสดีค่ะคุณ {holder.full_name} มีอะไรให้สอบถามไหมคะ",
            "current_class": None,
            "next_class": None,
            "exam_today": None,
        }

    now = current_dt or datetime.now()
    day_of_week = now.weekday()  # 0=Monday ... 6=Sunday
    current_time_str = now.strftime("%H:%M")
    current_time = now.time()
    today_date_str = now.strftime("%Y-%m-%d")

    # 1. Check for exams today
    exams_today = (
        db.query(ExamEntry)
        .filter(ExamEntry.student_id == holder.id, ExamEntry.exam_date == today_date_str)
        .order_by(ExamEntry.start_time)
        .all()
    )

    exam_info = None
    if exams_today:
        ex = exams_today[0]
        room_label = f"ห้อง {ex.room.room_number}" if ex.room else "ไม่ระบุห้อง"
        exam_info = {
            "course_code": ex.course.code,
            "course_name": ex.course.name_th,
            "exam_type": "ปลายภาค" if ex.exam_type == "final" else "กลางภาค",
            "start_time": ex.start_time,
            "end_time": ex.end_time,
            "room": room_label,
        }

    # 2. Check today's classes
    today_schedules = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.student_id == holder.id, ScheduleEntry.day_of_week == day_of_week)
        .order_by(ScheduleEntry.start_time)
        .all()
    )

    ongoing_class = None
    next_class = None
    status = "normal"
    minutes_late = 0
    minutes_until_next = None

    for entry in today_schedules:
        start_t = _parse_time_str(entry.start_time)
        end_t = _parse_time_str(entry.end_time)
        room_name = (
            f"ห้อง {entry.room.room_number} (ชั้น {entry.room.floor})"
            if entry.room
            else "ไม่ระบุห้อง"
        )
        item = {
            "course_code": entry.course.code,
            "course_name": entry.course.name_th,
            "start_time": entry.start_time,
            "end_time": entry.end_time,
            "room": room_name,
        }

        # Check if right now is within class hours
        if start_t <= current_time <= end_t:
            ongoing_class = item
            # Calculate how many minutes since class began
            diff_minutes = (current_time.hour * 60 + current_time.minute) - (
                start_t.hour * 60 + start_t.minute
            )
            minutes_late = max(0, diff_minutes)
            break
        elif start_t > current_time:
            if next_class is None:
                next_class = item
                diff_minutes = (start_t.hour * 60 + start_t.minute) - (
                    current_time.hour * 60 + current_time.minute
                )
                minutes_until_next = diff_minutes

    first_name = holder.full_name.split()[0]

    # 3. Generate dynamic smart greeting & status
    if exam_info:
        status = "exam_today"
        smart_greeting = (
            f"สวัสดีครับคุณ {first_name} วันนี้คุณมีสอบวิชา {exam_info['course_code']} "
            f"{exam_info['course_name']} ({exam_info['exam_type']}) เวลา {exam_info['start_time']} - "
            f"{exam_info['end_time']} น. ที่{exam_info['room']} ขอให้โชคดีกับการสอบนะครับ"
        )
        message = f"วันนี้มีสอบวิชา {exam_info['course_code']} {exam_info['room']}"
    elif ongoing_class:
        if minutes_late >= 10:
            status = "ongoing_late"
            smart_greeting = (
                f"สวัสดีครับคุณ {first_name} ตอนนี้มีเรียนวิชา {ongoing_class['course_code']} "
                f"{ongoing_class['course_name']} เวลา {ongoing_class['start_time']} - {ongoing_class['end_time']} น. "
                f"ที่{ongoing_class['room']} ตอนนี้เลยเวลาเริ่มเรียนมา {minutes_late} นาทีแล้ว สายแล้วนะ! รีบเข้าห้องเรียนนะครับ"
            )
            message = f"กำลังเรียนวิชา {ongoing_class['course_code']} (สาย {minutes_late} นาที)"
        else:
            status = "ongoing_in_class"
            smart_greeting = (
                f"สวัสดีครับคุณ {first_name} ตอนนี้มีเรียนวิชา {ongoing_class['course_code']} "
                f"{ongoing_class['course_name']} เวลา {ongoing_class['start_time']} - {ongoing_class['end_time']} น. "
                f"ที่{ongoing_class['room']} อาจารย์กำลังสอนอยู่ รีบเข้าห้องเรียนนะครับ"
            )
            message = f"กำลังเรียนวิชา {ongoing_class['course_code']} ({ongoing_class['room']})"
    elif next_class:
        if minutes_until_next is not None and minutes_until_next <= 45:
            status = "upcoming_soon"
            smart_greeting = (
                f"สวัสดีครับคุณ {first_name} อีก {minutes_until_next} นาที มีเรียนวิชา {next_class['course_code']} "
                f"{next_class['course_name']} เวลา {next_class['start_time']} น. ที่{next_class['room']} "
                f"อย่าลืมเตรียมตัวเข้าเรียนนะครับ"
            )
            message = f"วิชาต่อไป: {next_class['course_code']} เวลา {next_class['start_time']} น. (อีก {minutes_until_next} นาที)"
        else:
            status = "upcoming_later"
            smart_greeting = (
                f"สวัสดีครับคุณ {first_name} วันนี้คุณมีเรียนวิชา {next_class['course_code']} "
                f"{next_class['course_name']} เวลา {next_class['start_time']} - {next_class['end_time']} น. "
                f"ที่{next_class['room']} ครับ มีอะไรให้ช่วยสอบถามได้เลยครับ"
            )
            message = f"วิชาถัดไปวันนี้: {next_class['course_code']} เวลา {next_class['start_time']} น."
    elif today_schedules:
        status = "finished_today"
        smart_greeting = (
            f"สวัสดีครับคุณ {first_name} สำหรับวันนี้คุณเรียนครบทุกวิชาตามตารางแล้วครับ "
            f"มีข้อสงสัยเรื่องประกาศหรือสถานที่สอบถามได้เลยครับ"
        )
        message = "เรียนครบทุกวิชาสำหรับวันนี้แล้ว"
    else:
        status = "no_classes_today"
        smart_greeting = (
            f"สวัสดีครับคุณ {first_name} วัน{_DAY_NAMES_TH[day_of_week]}นี้ไม่มีตารางเรียนครับ "
            f"สอบถามข้อมูลอาคาร สถานที่ หรือเรื่องอื่น ๆ ได้เลยครับ"
        )
        message = f"วัน{_DAY_NAMES_TH[day_of_week]} ไม่มีตารางเรียน"

    return {
        "has_schedule": True,
        "day_of_week": day_of_week,
        "day_name_th": _DAY_NAMES_TH[day_of_week],
        "current_time": current_time_str,
        "status": status,
        "minutes_late": minutes_late,
        "minutes_until_next": minutes_until_next,
        "message": message,
        "smart_greeting": smart_greeting,
        "current_class": ongoing_class,
        "next_class": next_class,
        "exam_today": exam_info,
    }

