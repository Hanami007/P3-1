"""Render the public department data in the DB as plain text for the
chatbot's system prompt. The whole dataset is small (a few thousand tokens),
so it is sent in full on every request instead of retrieved piecemeal --
and read fresh each time, so edits to the DB show up without a restart."""

from sqlalchemy.orm import Session, selectinload

from app.models import Announcement, Building, DepartmentInfo, Personnel, ProblemContact, UniversityInfo


def _join(*parts: str | None) -> str:
    return " | ".join(p for p in parts if p)


def build_knowledge_context(db: Session) -> str:
    lines: list[str] = []

    uni = db.query(UniversityInfo).first()
    if uni:
        lines.append("## เกี่ยวกับมหาวิทยาลัย")
        lines.append(f"ชื่อ: {uni.name_th}" + (f" ({uni.name_en})" if uni.name_en else ""))
        for label, value in [
            ("ก่อตั้ง", uni.founded_year),
            ("ที่ตั้ง", uni.location),
            ("วิทยาเขต", uni.campuses),
            ("จุดเด่น", uni.about),
            ("Website", uni.website),
        ]:
            if value:
                lines.append(f"{label}: {value}")

    dept = db.query(DepartmentInfo).first()
    if dept:
        lines.append("## ข้อมูลสาขา")
        lines.append(f"ชื่อ: {dept.name_th}" + (f" ({dept.name_en})" if dept.name_en else ""))
        for label, value in [
            ("ที่ตั้ง", dept.address),
            ("เวลาทำการ", dept.office_hours),
            ("โทร", dept.phone),
            ("Email", dept.email),
            ("Facebook", dept.facebook),
            ("LINE", dept.line),
            ("Website", dept.website),
        ]:
            if value:
                lines.append(f"{label}: {value}")

    personnels = db.query(Personnel).order_by(Personnel.position, Personnel.id).all()
    if personnels:
        lines.append("\n## บุคลากร")
        for group, heading in [("lecturer", "อาจารย์"), ("staff", "เจ้าหน้าที่")]:
            members = [p for p in personnels if p.position == group]
            if not members:
                continue
            lines.append(f"{heading}:")
            for p in members:
                room = f"ห้อง {p.room.room_number} {p.room.building.spoken_name}" if p.room else None
                lines.append("- " + _join(p.display_name, room, p.phone, p.email))

    buildings = db.query(Building).options(selectinload(Building.rooms)).order_by(Building.code).all()
    if buildings:
        lines.append("\n## อาคารและห้อง (ตัวเลขคือหมายเลขตึกของมหาวิทยาลัย)")
        for b in buildings:
            short = f"เรียกสั้น ๆ ว่า {b.short_name}" if b.short_name else None
            lines.append("- " + _join(f"ตึก {b.code} {b.name_th}", short, b.description))
            for r in b.rooms:
                floor = f"ชั้น {r.floor}" if r.floor is not None else None
                lines.append("  - " + _join(r.room_number, floor, r.room_type))

    contacts = db.query(ProblemContact).order_by(ProblemContact.sort_order, ProblemContact.id).all()
    if contacts:
        lines.append("\n## เมื่อมีปัญหา ต้องติดต่อที่ไหน")
        for c in contacts:
            where = _join(
                c.office,
                f"{c.building.spoken_name} (อาคาร {c.building.code})" if c.building else None,
                c.location_note,
                c.phone,
            )
            lines.append(f"- {c.topic}: {where}")

    announcements = (
        db.query(Announcement).filter(Announcement.audience == "all").order_by(Announcement.created_at.desc()).limit(5).all()
    )
    if announcements:
        lines.append("\n## ประกาศล่าสุด")
        for a in announcements:
            lines.append(f"- {a.title}: {a.body}")

    return "\n".join(lines)
