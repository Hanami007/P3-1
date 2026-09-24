from datetime import datetime, time
from sqlalchemy.orm import Session

from app.models import CardHolder, ExamEntry, Role, ScheduleEntry
from app.services.student_data import exams_query, schedule_query

_DAY_NAMES_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


def room_label(room) -> str:
    if room is None:
        return "ไม่ระบุห้อง"
    label = f"ห้อง {room.room_number}"
    if room.floor is not None:
        label += f" (ชั้น {room.floor})"
    if room.building is not None:
        # Include the name, not just the number -- students know it as
        # "ตึกวิท", and the chatbot repeats whatever it is given here.
        label += f" {room.building.spoken_name} (อาคาร {room.building.code})"
    return label


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
        exams_query(db, holder.id)
        .filter(ExamEntry.exam_date == today_date_str)
        .order_by(ExamEntry.start_time)
        .all()
    )

    exam_info = None
    if exams_today:
        ex = exams_today[0]
        exam_info = {
            "course_code": ex.course.code,
            "course_name": ex.course.name_th,
            "exam_type": "ปลายภาค" if ex.exam_type == "final" else "กลางภาค",
            "start_time": ex.start_time,
            "end_time": ex.end_time,
            "room": room_label(ex.room),
        }

    # 2. Check today's classes
    today_schedules = (
        schedule_query(db, holder.id)
        .filter(ScheduleEntry.day_of_week == day_of_week)
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
        room_name = room_label(entry.room)
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
    # full_name may carry a Thai title ("นายจักรพรรดิ์") -- greet by name only.
    for prefix in ("นางสาว", "นาย", "นาง"):
        if first_name.startswith(prefix) and len(first_name) > len(prefix):
            first_name = first_name[len(prefix):]
            break

    # 3. Generate dynamic smart greeting & status.
    # Kept short and casual on purpose -- this gets spoken aloud (TTS) the
    # moment someone is recognized, so it should sound like a friend giving
    # a quick heads-up, not a formal announcement reciting every detail.
    # The exact times/rooms still go in `message` and the structured
    # current_class/next_class/exam_today fields for on-screen display.
    if exam_info:
        status = "exam_today"
        smart_greeting = f"{first_name} วันนี้มีสอบวิชา{exam_info['course_name']}นะ ขอให้โชคดี!"
        message = f"วันนี้มีสอบวิชา {exam_info['course_code']} {exam_info['room']}"
    elif ongoing_class:
        if minutes_late >= 10:
            status = "ongoing_late"
            smart_greeting = f"{first_name} ตอนนี้เข้าเรียนวิชา{ongoing_class['course_name']}สายไปแล้ว {minutes_late} นาทีนะ รีบไปเลย!"
            message = f"กำลังเรียนวิชา {ongoing_class['course_code']} (สาย {minutes_late} นาที)"
        else:
            status = "ongoing_in_class"
            smart_greeting = f"{first_name} ตอนนี้ถึงเวลาเรียนวิชา{ongoing_class['course_name']}แล้วนะ ไปเข้าห้องเรียนกันเถอะ!"
            message = f"กำลังเรียนวิชา {ongoing_class['course_code']} ({ongoing_class['room']})"
    elif next_class:
        if minutes_until_next is not None and minutes_until_next <= 45:
            status = "upcoming_soon"
            smart_greeting = f"{first_name} อีก {minutes_until_next} นาทีจะถึงเวลาเรียนวิชา{next_class['course_name']}แล้วนะ เตรียมตัวได้เลย"
            message = f"วิชาต่อไป: {next_class['course_code']} เวลา {next_class['start_time']} น. (อีก {minutes_until_next} นาที)"
        else:
            status = "upcoming_later"
            smart_greeting = f"สวัสดี {first_name} วันนี้มีเรียนวิชา{next_class['course_name']}ด้วยนะ มีอะไรให้ช่วยถามได้เลย"
            message = f"วิชาถัดไปวันนี้: {next_class['course_code']} เวลา {next_class['start_time']} น."
    elif today_schedules:
        status = "finished_today"
        smart_greeting = f"{first_name} วันนี้เรียนครบทุกวิชาแล้วนะ พักผ่อนได้เลย มีอะไรให้ช่วยถามได้"
        message = "เรียนครบทุกวิชาสำหรับวันนี้แล้ว"
    else:
        status = "no_classes_today"
        smart_greeting = f"สวัสดี {first_name} วัน{_DAY_NAMES_TH[day_of_week]}นี้ไม่มีเรียนนะ มีอะไรให้ช่วยถามได้เลย"
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

