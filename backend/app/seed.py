"""Populate the SQLite database with sample data for demoing the kiosk.

Safe to run multiple times: every row is looked up by its natural key
(card_uid, course code, building code, etc.) and only inserted if missing,
so adding more sample data later just means adding more entries below and
re-running.

Run with: python -m app.seed
"""

from app.database import Base, SessionLocal, engine
from app.models import (
    Announcement,
    Building,
    CardHolder,
    Course,
    ExamEntry,
    Role,
    Room,
    ScheduleEntry,
)


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
        cs_building, _ = get_or_create(
            db,
            Building,
            {"code": "CS-A"},
            {
                "name_th": "อาคารวิทยาการคอมพิวเตอร์",
                "name_en": "Computer Science Building",
                "description": "ห้องเรียน ห้องปฏิบัติการ และห้องธุรการของสาขาวิทยาการคอมพิวเตอร์",
            },
        )
        get_or_create(db, Building, {"code": "LIB"}, {"name_th": "สำนักหอสมุด", "name_en": "Library"})

        room_301, _ = get_or_create(db, Room, {"building_id": cs_building.id, "room_number": "301"}, {"floor": 3, "room_type": "lecture"})
        room_401, _ = get_or_create(db, Room, {"building_id": cs_building.id, "room_number": "401"}, {"floor": 4, "room_type": "lab"})
        room_402, _ = get_or_create(db, Room, {"building_id": cs_building.id, "room_number": "402"}, {"floor": 4, "room_type": "lab"})

        courses = {}
        for code, name_th, name_en, credits in [
            ("CS201", "โครงสร้างข้อมูลและอัลกอริทึม", "Data Structures and Algorithms", 3),
            ("CS210", "การเขียนโปรแกรมเชิงวัตถุ", "Object-Oriented Programming", 3),
            ("CS220", "ระบบฐานข้อมูล", "Database Systems", 3),
            ("CS305", "วิศวกรรมซอฟต์แวร์", "Software Engineering", 3),
            ("CS310", "ปัญญาประดิษฐ์เบื้องต้น", "Introduction to Artificial Intelligence", 3),
            ("GE101", "ภาษาอังกฤษเพื่อการสื่อสาร", "English for Communication", 2),
        ]:
            courses[code], _ = get_or_create(
                db, Course, {"code": code}, {"name_th": name_th, "name_en": name_en, "credits": credits}
            )

        student, _ = get_or_create(
            db,
            CardHolder,
            {"card_uid": "04A1B2C3"},
            {
                "student_id": "6604101335",
                "full_name": "นักศึกษาวิทคอม ทดสอบ",
                "program": "วิทยาการคอมพิวเตอร์",
                "role": Role.CS_STUDENT,
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

        # day_of_week: 0=จันทร์ ... 4=ศุกร์
        weekly_schedule = [
            ("CS201", 0, "09:00", "12:00", room_301),
            ("CS210", 0, "13:00", "15:00", room_401),
            ("CS220", 1, "09:00", "12:00", room_301),
            ("CS305", 2, "13:00", "16:00", room_401),
            ("CS310", 3, "09:00", "11:00", room_402),
            ("GE101", 4, "13:00", "15:00", room_301),
        ]
        for code, day, start, end, room in weekly_schedule:
            get_or_create(
                db,
                ScheduleEntry,
                {"student_id": student.id, "course_id": courses[code].id, "day_of_week": day},
                {"section": "1", "start_time": start, "end_time": end, "room_id": room.id},
            )

        exams = [
            ("CS201", "2026-10-05", "09:00", "11:00", room_301, "midterm"),
            ("CS210", "2026-10-06", "09:00", "11:00", room_401, "midterm"),
            ("CS220", "2026-12-08", "09:00", "11:00", room_301, "final"),
            ("CS305", "2026-12-10", "13:00", "15:00", room_401, "final"),
        ]
        for code, exam_date, start, end, room, exam_type in exams:
            get_or_create(
                db,
                ExamEntry,
                {"student_id": student.id, "course_id": courses[code].id, "exam_date": exam_date},
                {"start_time": start, "end_time": end, "room_id": room.id, "exam_type": exam_type},
            )

        get_or_create(
            db,
            Announcement,
            {"title": "เปิดรับสมัครโครงงานพิเศษ ปีการศึกษา 2569"},
            {
                "body": "นักศึกษาวิทคอมชั้นปีที่ 3-4 สามารถยื่นหัวข้อโครงงานพิเศษได้ที่ห้องธุรการสาขา ตั้งแต่บัดนี้ถึงสิ้นเดือน",
                "audience": "cs_student",
            },
        )

        db.commit()
        print("Seed data ensured (existing rows left untouched, missing rows inserted).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
