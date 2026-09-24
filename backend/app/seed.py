"""Populate the SQLite database with the department's real reference data
plus a demo student.

Safe to run multiple times: every row is looked up by its natural key
(card_uid, course code, building code, etc.) and only inserted if missing,
so adding more data later just means adding more entries below and
re-running. Existing rows are NOT updated -- to change a value, edit it in
the DB or delete backend/kiosk.db and re-seed.

Run with: python -m app.seed
"""

from app.database import Base, SessionLocal, engine
from app.models import (
    Building,
    CardHolder,
    Course,
    CourseSection,
    DepartmentInfo,
    Enrollment,
    ExamEntry,
    Personnel,
    ProblemContact,
    Role,
    Room,
    ScheduleEntry,
    UniversityInfo,
)

TERM = "1/2569"

BUILDINGS = [
    ("105", "คณะวิทยาศาสตร์ (อาคาร 60 ปี)", "สาขาวิชาวิทยาการคอมพิวเตอร์อยู่ชั้น 6"),
    ("141", "อาคารจุฬาภรณ์", None),
    ("101", "อาคารพัฒนาวิสัยทัศน์", "สำนักทะเบียน, กองคลัง"),
    ("102", "อาคารประเสริฐ ณ นคร (คณะศิลปศาสตร์)", None),
    ("103", "อาคารสมิตตานนท์", None),
    ("104", "คณะวิศวกรรมและอุตสาหกรรมเกษตร", None),
    ("107", "คณะบริหารธุรกิจ", None),
    ("140", "อาคารเศรษฐศาสตร์", None),
    ("142", "อาคารเทพ พงษ์พานิช", None),
    ("143", "อาคาร 75 ปี (คณะสารสนเทศ)", None),
    ("144", "สระว่ายน้ำ", None),
    ("145", "วิทยาลัยพลังงานทดแทน", None),
    ("147", "อาคารเรียนรวม 80 ปี", None),
    ("149", "อาคารศูนย์ภาษา", None),
    ("150", "อาคารพยาบาลศาสตร์", None),
]

# What students call each building when speaking; others fall back to name_th.
SHORT_NAMES = {
    "105": "ตึกวิท",
}

# (building code, room name, floor or None if unknown, room type)
ROOMS = [
    ("105", "บรรยาย คอม 6", None, "lecture"),
    ("105", "บรรยาย คอม 7", None, "lecture"),
    ("105", "บรรยาย คอม 8", None, "lecture"),
    ("105", "บรรยาย ไอที 1", None, "lecture"),
    ("105", "บรรยาย ไอที 2", None, "lecture"),
    *[("105", f"Lab คอม {n}", None, "lab") for n in range(1, 6)],
    *[("105", f"Lab ไอที {n}", None, "lab") for n in (1, 2, 5)],
    ("105", "สำนักงานสาขาวิทยาการคอมพิวเตอร์", 6, "office"),
    *[("141", n, None, "lecture") for n in ("3100", "3102", "3202", "3203", "3303", "3402", "3403A", "3403B")],
]

# (title, full name, position)
PERSONNELS = [
    ("อ.ดร.", "กิตติกร หาญตระกูล", "lecturer"),
    ("ผศ.", "ก่องกาญจน์ ดุลยไชย", "lecturer"),
    ("ผศ.ดร.", "ปวีณ เขื่อนแก้ว", "lecturer"),
    ("อ.ดร.", "พยุงศักดิ์ เกษมสำราญ", "lecturer"),
    ("ผศ.ดร.", "พาสน์ ปราโมกข์ชน", "lecturer"),
    ("ผศ.", "ภานุวัฒน์ เมฆะ", "lecturer"),
    ("ผศ.ดร.", "สนิท สิทธิ", "lecturer"),
    ("ผศ.ดร.", "สมนึก สินธุปวน", "lecturer"),
    ("อ.", "อรรถวิท ชังคมานนท์", "lecturer"),
    ("อ.", "อลงกต กองมณี", "lecturer"),
    ("นางสาว", "ช่อทิพย์ สิทธิ", "staff"),
    ("นาย", "ประทีป สุขสมัย", "staff"),
    ("นาง", "ปราณี กันธิมา", "staff"),
    ("นางสาว", "พัชรี ยางยืน", "staff"),
    ("นางสาว", "สุภาพรรณ อนุตรกุล", "staff"),
]

COURSES = [
    ("10300498", "การเรียนรู้อิสระ", 3),
    ("10301366", "วิทยาการสมองกลฝังตัว", 3),
    ("10301491", "สัมมนาวิชาการทางวิทยาการคอมพิวเตอร์", 3),
]

# (course code, day 0=จันทร์, start, end, building, room)
SESSIONS = [
    ("10301491", 0, "09:00", "10:00", "105", "บรรยาย คอม 8"),
    ("10301366", 0, "13:00", "15:00", "105", "Lab คอม 5"),
    ("10301366", 1, "10:00", "12:00", "105", "Lab คอม 5"),
]

# (topic, office, building code or None, location note, phone)
PROBLEM_CONTACTS = [
    ("ลงทะเบียน/ตารางเรียน", "สำนักทะเบียน", "101", None, "053-873000"),
    ("การเงิน/ทุนการศึกษา", "กองคลัง", "101", None, "053-873000"),
    ("เจ็บป่วย", "หน่วยพยาบาล", None, None, "053-873000"),
    ("ปัญหาในสาขาวิทยาการคอมพิวเตอร์", "สำนักงานสาขาวิทยาการคอมพิวเตอร์", "105", "ชั้น 6", "053-873890-3"),
    ("หอพัก", "หอพักนักศึกษา", None, None, None),
    ("บัตรนักศึกษาหาย", "สำนักทะเบียน", "101", None, "053-873000"),
    ("ปัญหาทั่วไป", "สำนักงานมหาวิทยาลัย", None, None, None),
]


def get_or_create(db, model, lookup: dict, defaults: dict | None = None):
    instance = db.query(model).filter_by(**lookup).first()
    if instance:
        return instance, False
    instance = model(**lookup, **(defaults or {}))
    db.add(instance)
    db.flush()
    return instance, True


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # university_info is single-row; `name_th` is its natural key.
        get_or_create(
            db,
            UniversityInfo,
            {"name_th": "มหาวิทยาลัยแม่โจ้"},
            {
                "name_en": "Maejo University",
                "founded_year": "เริ่มก่อตั้งเป็นโรงเรียนฝึกหัดครูประถมกสิกรรมปี พ.ศ. 2477 "
                "และยกฐานะเป็นมหาวิทยาลัยแม่โจ้ในปี พ.ศ. 2539",
                "location": "ตำบลหนองหาร อำเภอสันทราย จังหวัดเชียงใหม่",
                "campuses": "วิทยาเขตหลักเชียงใหม่ วิทยาเขตแม่โจ้-แพร่ เฉลิมพระเกียรติ และวิทยาเขตแม่โจ้-ชุมพร",
                "about": "มีชื่อเสียงด้านเกษตรศาสตร์ ทรัพยากรธรรมชาติ และสิ่งแวดล้อม "
                "ภายใต้แนวคิด Green and Eco University เน้นเกษตรอินทรีย์และความยั่งยืน",
                "website": "https://www.mju.ac.th",
            },
        )

        # department_info is single-row; `name_th` is its natural key.
        get_or_create(
            db,
            DepartmentInfo,
            {"name_th": "สาขาวิชาวิทยาการคอมพิวเตอร์ คณะวิทยาศาสตร์ มหาวิทยาลัยแม่โจ้"},
            {
                "name_en": "Department of Computer Science, Faculty of Science, Maejo University",
                "address": "ชั้น 6 อาคาร 60 ปี คณะวิทยาศาสตร์ (ตึก 105)",
                "phone": "053-873890-3",
                "email": "cs@mju.ac.th",
                "facebook": "https://www.facebook.com/computersciencemju",
                "line": "https://line.me/R/ti/p/@053vfccm",
                "website": "https://csmju.com",
                # TODO: fill in office_hours
            },
        )

        buildings = {}
        for code, name_th, description in BUILDINGS:
            buildings[code], _ = get_or_create(
                db,
                Building,
                {"code": code},
                {"name_th": name_th, "short_name": SHORT_NAMES.get(code), "description": description},
            )

        rooms = {}
        for bcode, name, floor, room_type in ROOMS:
            rooms[(bcode, name)], _ = get_or_create(
                db, Room, {"building_id": buildings[bcode].id, "room_number": name}, {"floor": floor, "room_type": room_type}
            )

        office = rooms[("105", "สำนักงานสาขาวิทยาการคอมพิวเตอร์")]
        personnels = {}
        for title, full_name, position in PERSONNELS:
            defaults = {"title": title, "position": position}
            if position == "staff":
                defaults["room_id"] = office.id
            personnels[full_name], _ = get_or_create(db, Personnel, {"full_name": full_name}, defaults)

        sections = {}
        for code, name_th, credits in COURSES:
            course, _ = get_or_create(db, Course, {"code": code}, {"name_th": name_th, "credits": credits})
            sections[code], _ = get_or_create(db, CourseSection, {"course_id": course.id, "section_no": "1", "term": TERM})
            # Exam dates not announced yet -- date/time/room stay NULL until then.
            for exam_type in ("midterm", "final"):
                get_or_create(db, ExamEntry, {"section_id": sections[code].id, "exam_type": exam_type})

        for code, day, start, end, bcode, room in SESSIONS:
            get_or_create(
                db,
                ScheduleEntry,
                {"section_id": sections[code].id, "day_of_week": day, "start_time": start},
                {"end_time": end, "room_id": rooms[(bcode, room)].id},
            )

        for order, (topic, office_name, bcode, note, phone) in enumerate(PROBLEM_CONTACTS, start=1):
            get_or_create(
                db,
                ProblemContact,
                {"topic": topic},
                {
                    "office": office_name,
                    "building_id": buildings[bcode].id if bcode else None,
                    "location_note": note,
                    "phone": phone,
                    "sort_order": order,
                },
            )

        advisor = personnels["กิตติกร หาญตระกูล"]
        demo_student, _ = get_or_create(
            db,
            CardHolder,
            {"student_id": "6604101313"},
            {
                # Placeholder until the real card is read -- face samples are
                # enrolled under app/data/faces/<card_uid>/, so rename that
                # folder and retrain when swapping in the real UID.
                "card_uid": "TEMP6604101313",
                "full_name": "นายจักรพรรดิ์ เจริญ",
                "program": "วิทยาการคอมพิวเตอร์",
                "role": Role.CS_STUDENT,
                "advisor_id": advisor.id,
            },
        )
        # Test card that already has enrolled face samples (app/data/faces/04A1B2C3),
        # kept so card-tap / face login can be demoed before the real card is read.
        face_demo, _ = get_or_create(
            db,
            CardHolder,
            {"card_uid": "04A1B2C3"},
            {
                "student_id": "6604101335",
                "full_name": "ธราเทพ จันทร์ดำ",
                "program": "วิทยาการคอมพิวเตอร์",
                "role": Role.CS_STUDENT,
                "advisor_id": advisor.id,
            },
        )
        get_or_create(
            db,
            CardHolder,
            {"card_uid": "04D4E5F6"},
            {"student_id": None, "full_name": "เจ้าหน้าที่สาขา", "program": None, "role": Role.STAFF},
        )
        get_or_create(
            db,
            CardHolder,
            {"card_uid": "04112233"},
            {
                "student_id": "6601234567",
                "full_name": "นักศึกษาสาขาอื่น ทดสอบ",
                "program": "เทคโนโลยีสารสนเทศ",
                "role": Role.OTHER_STUDENT,
            },
        )

        for student in (demo_student, face_demo):
            for section in sections.values():
                get_or_create(db, Enrollment, {"card_holder_id": student.id, "section_id": section.id})

        db.commit()
        print("Seed data ensured (existing rows left untouched, missing rows inserted).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
