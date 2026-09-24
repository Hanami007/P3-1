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
    UniversityInfo,
)
from app.routers.chatbot import _build_student_context
from app.services.knowledge import build_knowledge_context


def test_knowledge_context_includes_university_info(db_session):
    db_session.add(
        UniversityInfo(
            name_th="มหาวิทยาลัยแม่โจ้",
            name_en="Maejo University",
            location="อำเภอสันทราย จังหวัดเชียงใหม่",
            website="https://www.mju.ac.th",
        )
    )
    db_session.commit()

    text = build_knowledge_context(db_session)
    assert "มหาวิทยาลัยแม่โจ้" in text
    assert "Maejo University" in text
    assert "อำเภอสันทราย จังหวัดเชียงใหม่" in text
    assert "https://www.mju.ac.th" in text


def test_knowledge_context_reads_db(db_session):
    building = Building(code="105", name_th="คณะวิทยาศาสตร์ (อาคาร 60 ปี)")
    db_session.add_all(
        [
            DepartmentInfo(name_th="สาขาวิชาวิทยาการคอมพิวเตอร์", phone="053-873890-3"),
            Personnel(title="อ.ดร.", full_name="กิตติกร หาญตระกูล", position="lecturer"),
            building,
        ]
    )
    db_session.flush()
    db_session.add(ProblemContact(topic="บัตรหาย", office="สำนักทะเบียน", building_id=building.id))
    db_session.commit()

    text = build_knowledge_context(db_session)
    assert "053-873890-3" in text
    assert "อ.ดร. กิตติกร หาญตระกูล" in text
    assert "ตึก 105" in text
    assert "บัตรหาย: สำนักทะเบียน" in text


def test_student_context_handles_unannounced_exam(db_session):
    advisor = Personnel(title="อ.ดร.", full_name="กิตติกร หาญตระกูล", position="lecturer")
    course = Course(code="10301366", name_th="วิทยาการสมองกลฝังตัว")
    db_session.add_all([advisor, course])
    db_session.flush()
    holder = CardHolder(card_uid="S1", full_name="นักศึกษา ทดสอบ", role=Role.CS_STUDENT, advisor_id=advisor.id)
    section = CourseSection(course_id=course.id, section_no="1", term="1/2569")
    db_session.add_all([holder, section])
    db_session.flush()
    db_session.add_all(
        [
            Enrollment(card_holder_id=holder.id, section_id=section.id),
            ExamEntry(section_id=section.id, exam_type="midterm"),
        ]
    )
    db_session.commit()

    text = _build_student_context(db_session, holder)
    assert "อาจารย์ที่ปรึกษา: อ.ดร. กิตติกร หาญตระกูล" in text
    assert "ยังไม่ประกาศวันสอบ" in text
