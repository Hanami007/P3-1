import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, enum.Enum):
    CS_STUDENT = "cs_student"
    OTHER_STUDENT = "other_student"
    STAFF = "staff"
    ADMIN = "admin"
    GUEST = "guest"


class CardHolder(Base):
    """A person identified by an RFID/NFC card (student, staff, or admin)."""

    __tablename__ = "card_holders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    student_id: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(120))
    program: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.OTHER_STUDENT)
    is_active: Mapped[bool] = mapped_column(default=True)

    schedule_entries: Mapped[list["ScheduleEntry"]] = relationship(back_populates="student")
    exam_entries: Mapped[list["ExamEntry"]] = relationship(back_populates="student")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name_th: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    credits: Mapped[int] = mapped_column(Integer, default=3)

    schedule_entries: Mapped[list["ScheduleEntry"]] = relationship(back_populates="course")
    exam_entries: Mapped[list["ExamEntry"]] = relationship(back_populates="course")


class ScheduleEntry(Base):
    """One weekly class slot for a student."""

    __tablename__ = "schedule_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("card_holders.id"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    section: Mapped[str] = mapped_column(String(10), default="1")
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Mon .. 6=Sun
    start_time: Mapped[str] = mapped_column(String(5))  # "09:00"
    end_time: Mapped[str] = mapped_column(String(5))  # "12:00"
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)

    student: Mapped["CardHolder"] = relationship(back_populates="schedule_entries")
    course: Mapped["Course"] = relationship(back_populates="schedule_entries")
    room: Mapped["Room | None"] = relationship()


class ExamEntry(Base):
    __tablename__ = "exam_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("card_holders.id"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    exam_date: Mapped[str] = mapped_column(String(10))  # "2026-10-05"
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    exam_type: Mapped[str] = mapped_column(String(20), default="final")  # midterm/final

    student: Mapped["CardHolder"] = relationship(back_populates="exam_entries")
    course: Mapped["Course"] = relationship(back_populates="exam_entries")
    room: Mapped["Room | None"] = relationship()


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name_th: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    rooms: Mapped[list["Room"]] = relationship(back_populates="building")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    room_number: Mapped[str] = mapped_column(String(20))
    floor: Mapped[int] = mapped_column(Integer, default=1)
    room_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # lab/lecture/office

    building: Mapped["Building"] = relationship(back_populates="rooms")


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
