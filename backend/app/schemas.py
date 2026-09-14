from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Role


class CardScanRequest(BaseModel):
    card_uid: str


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_number: str
    floor: int
    room_type: str | None = None


class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name_th: str
    name_en: str | None = None
    description: str | None = None
    rooms: list[RoomOut] = []


class CardHolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: str | None = None
    full_name: str
    program: str | None = None
    role: Role


class CardScanResponse(BaseModel):
    recognized: bool
    holder: CardHolderOut | None = None
    role: Role
    message: str


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name_th: str
    name_en: str | None = None
    credits: int


class ScheduleEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    section: str
    day_of_week: int
    start_time: str
    end_time: str
    course: CourseOut
    room: RoomOut | None = None


class ExamEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exam_date: str
    start_time: str
    end_time: str
    exam_type: str
    course: CourseOut
    room: RoomOut | None = None


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    body: str
    audience: str
    created_at: datetime


class ChatRequest(BaseModel):
    message: str
    card_uid: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str


class AccessLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    card_uid: str | None = None
    role: str | None = None
    action: str
    detail: str | None = None
    granted: bool
    timestamp: datetime


class WakeEvent(BaseModel):
    detected: bool
    timestamp: datetime
