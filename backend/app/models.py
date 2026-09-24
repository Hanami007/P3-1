import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, enum.Enum):
    CS_STUDENT = "cs_student"
    OTHER_STUDENT = "other_student"
    STAFF = "staff"
    ADMIN = "admin"
    GUEST = "guest"


class DepartmentInfo(Base):
    """Single-row table: the department's own contact details."""

    __tablename__ = "department_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_th: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    facebook: Mapped[str | None] = mapped_column(String(200), nullable=True)
    line: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(200), nullable=True)
    office_hours: Mapped[str | None] = mapped_column(String(200), nullable=True)


class UniversityInfo(Base):
    """Single-row table: general facts about the whole university (not just
    this department) -- history, location, campuses. Answers "แม่โจ้คือ
    มหาวิทยาลัยอะไร" / "ก่อตั้งเมื่อไหร่" style questions from any visitor."""

    __tablename__ = "university_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_th: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    founded_year: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    campuses: Mapped[str | None] = mapped_column(String(300), nullable=True)
    about: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    website: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Personnel(Base):
    """Lecturers and support staff (not card holders -- they may not have a card)."""

    __tablename__ = "personnels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(50))  # "ผศ.ดร.", "อ.", "นางสาว" ...
    full_name: Mapped[str] = mapped_column(String(120), unique=True)
    position: Mapped[str] = mapped_column(String(20))  # lecturer/staff
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)

    room: Mapped["Room | None"] = relationship()

    @property
    def display_name(self) -> str:
        return f"{self.title} {self.full_name}"


class CardHolder(Base):
    """A person identified by an RFID/NFC card (student, staff, or admin)."""

    __tablename__ = "card_holders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Nullable so a student can be registered before their card is read;
    # SQLite allows many NULLs under a UNIQUE constraint.
    card_uid: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    student_id: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(120))
    program: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.OTHER_STUDENT)
    is_active: Mapped[bool] = mapped_column(default=True)
    advisor_id: Mapped[int | None] = mapped_column(ForeignKey("personnels.id"), nullable=True)

    advisor: Mapped["Personnel | None"] = relationship()
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="card_holder")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name_th: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    credits: Mapped[int] = mapped_column(Integer, default=3)

    sections: Mapped[list["CourseSection"]] = relationship(back_populates="course")


class CourseSection(Base):
    """One offering of a course in a term. Class times and exams belong to the
    section, so students in the same section share one set of rows."""

    __tablename__ = "course_sections"
    __table_args__ = (UniqueConstraint("course_id", "section_no", "term"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    section_no: Mapped[str] = mapped_column(String(10), default="1")
    term: Mapped[str] = mapped_column(String(10))  # "1/2569"

    course: Mapped["Course"] = relationship(back_populates="sections")
    sessions: Mapped[list["ScheduleEntry"]] = relationship(back_populates="course_section")
    exams: Mapped[list["ExamEntry"]] = relationship(back_populates="course_section")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="section")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("card_holder_id", "section_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_holder_id: Mapped[int] = mapped_column(ForeignKey("card_holders.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("course_sections.id"))

    card_holder: Mapped["CardHolder"] = relationship(back_populates="enrollments")
    section: Mapped["CourseSection"] = relationship(back_populates="enrollments")


class ScheduleEntry(Base):
    """One weekly class slot of a section."""

    __tablename__ = "schedule_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("course_sections.id"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Mon .. 6=Sun
    start_time: Mapped[str] = mapped_column(String(5))  # "09:00"
    end_time: Mapped[str] = mapped_column(String(5))  # "12:00"
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)

    course_section: Mapped["CourseSection"] = relationship(back_populates="sessions")
    room: Mapped["Room | None"] = relationship()

    @property
    def course(self) -> "Course":
        return self.course_section.course

    @property
    def section(self) -> str:
        return self.course_section.section_no


class ExamEntry(Base):
    __tablename__ = "exam_entries"
    __table_args__ = (UniqueConstraint("section_id", "exam_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("course_sections.id"))
    exam_type: Mapped[str] = mapped_column(String(20), default="final")  # midterm/final
    # Date/time/room stay NULL until the university announces them.
    exam_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "2026-10-05"
    start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)

    course_section: Mapped["CourseSection"] = relationship(back_populates="exams")
    room: Mapped["Room | None"] = relationship()

    @property
    def course(self) -> "Course":
        return self.course_section.course


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)  # university building number, e.g. "105"
    name_th: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # What students actually call it ("ตึกวิท") -- used when speaking.
    short_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Path under /static, e.g. "/static/buildings/105.jpg" -- see
    # backend/app/static/buildings/README.md for how to add real photos.
    image_url: Mapped[str | None] = mapped_column(String(300), nullable=True)

    rooms: Mapped[list["Room"]] = relationship(back_populates="building")

    @property
    def spoken_name(self) -> str:
        return self.short_name or self.name_th


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("building_id", "room_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    room_number: Mapped[str] = mapped_column(String(50))  # "3100" or a name like "Lab คอม 5"
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    room_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # lab/lecture/office

    building: Mapped["Building"] = relationship(back_populates="rooms")


class ProblemContact(Base):
    """"I have a problem with X -- where do I go?" directory for any visitor."""

    __tablename__ = "problem_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(100), unique=True)
    office: Mapped[str] = mapped_column(String(200))
    building_id: Mapped[int | None] = mapped_column(ForeignKey("buildings.id"), nullable=True)
    location_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    building: Mapped["Building | None"] = relationship()


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(2000))
    audience: Mapped[str] = mapped_column(String(20), default="all")  # all/cs_student/staff
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AccessLog(Base):
    """Audit trail of every card tap / kiosk interaction."""

    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    card_holder_id: Mapped[int | None] = mapped_column(ForeignKey("card_holders.id"), nullable=True)
    role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    action: Mapped[str] = mapped_column(String(50))  # card_scan/chat/wake/schedule_view/denied
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    granted: Mapped[bool] = mapped_column(default=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
