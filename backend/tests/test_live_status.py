from datetime import datetime
from app.models import CardHolder, Course, ExamEntry, Role, Room, ScheduleEntry
from app.services.live_status import calculate_student_live_status


def test_live_status_ongoing_late(db_session):
    # Setup student, course, room
    holder = CardHolder(card_uid="TEST_STUDENT", full_name="สมชาย นักศึกษา", role=Role.CS_STUDENT)
    db_session.add(holder)
    db_session.flush()

    course = Course(code="CS201", name_th="โครงสร้างข้อมูล", credits=3)
    db_session.add(course)
    db_session.flush()

    room = Room(building_id=1, room_number="301", floor=3)
    db_session.add(room)
    db_session.flush()

    # Schedule on Monday (day 0) 09:00 - 12:00
    entry = ScheduleEntry(
        student_id=holder.id,
        course_id=course.id,
        day_of_week=0,
        start_time="09:00",
        end_time="12:00",
        room_id=room.id,
    )
    db_session.add(entry)
    db_session.commit()

    # Test at Monday 09:20 (20 minutes late)
    test_dt = datetime(2026, 9, 21, 9, 20)  # 2026-09-21 is Monday
    assert test_dt.weekday() == 0

    status = calculate_student_live_status(db_session, holder, current_dt=test_dt)
    assert status["status"] == "ongoing_late"
    assert status["minutes_late"] == 20
    # smart_greeting is spoken aloud (TTS), so it's kept short and casual --
    # course name + urgency, not a full recitation of code/room/exact times.
    assert "สาย" in status["smart_greeting"]
    assert "โครงสร้างข้อมูล" in status["smart_greeting"]
    # The precise course code and room still show up in the on-screen message.
    assert "CS201" in status["message"]
    assert "ห้อง 301" in status["current_class"]["room"]


def test_live_status_upcoming_soon(db_session):
    holder = CardHolder(card_uid="TEST_STUDENT2", full_name="สมหญิง ใจดี", role=Role.CS_STUDENT)
    db_session.add(holder)
    db_session.flush()

    course = Course(code="CS220", name_th="ฐานข้อมูล", credits=3)
    db_session.add(course)
    db_session.flush()

    entry = ScheduleEntry(
        student_id=holder.id,
        course_id=course.id,
        day_of_week=0,
        start_time="10:00",
        end_time="12:00",
    )
    db_session.add(entry)
    db_session.commit()

    # Test at Monday 09:40 (20 minutes before class)
    test_dt = datetime(2026, 9, 21, 9, 40)
    status = calculate_student_live_status(db_session, holder, current_dt=test_dt)
    assert status["status"] == "upcoming_soon"
    assert status["minutes_until_next"] == 20
    assert "เตรียมตัว" in status["smart_greeting"]


def test_scan_with_noise_metrics(client):
    resp = client.post(
        "/api/cards/scan",
        json={
            "card_uid": "STUDENT1",
            "ambient_noise_db": 48.5,
            "peak_noise_db": 82.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["recognized"] is True
    assert data["smart_greeting"] is not None
    # High peak noise should have added warning
    assert "ตรวจพบเสียงรบกวนรอบข้างค่อนข้างดัง" in data["smart_greeting"]

