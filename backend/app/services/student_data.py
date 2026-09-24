"""Queries for one student's own timetable, resolved through their enrollments."""

from sqlalchemy.orm import Query, Session

from app.models import CourseSection, Enrollment, ExamEntry, ScheduleEntry


def schedule_query(db: Session, card_holder_id: int) -> Query:
    return (
        db.query(ScheduleEntry)
        .join(ScheduleEntry.course_section)
        .join(CourseSection.enrollments)
        .filter(Enrollment.card_holder_id == card_holder_id)
    )


def exams_query(db: Session, card_holder_id: int) -> Query:
    return (
        db.query(ExamEntry)
        .join(ExamEntry.course_section)
        .join(CourseSection.enrollments)
        .filter(Enrollment.card_holder_id == card_holder_id)
    )
