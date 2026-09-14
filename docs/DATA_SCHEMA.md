# โครงสร้างข้อมูล (Data Schema)

ตารางทั้งหมดกำหนดไว้ที่ `backend/app/models.py` (SQLAlchemy ORM, ใช้ได้ทั้ง SQLite และ MySQL
โดยเปลี่ยนแค่ `DATABASE_URL`)

| ตาราง | คำอธิบาย | ฟิลด์สำคัญ |
|---|---|---|
| `card_holders` | ผู้ถือบัตร (นักศึกษาวิทคอม/สาขาอื่น/บุคลากร) | `card_uid` (unique), `student_id`, `full_name`, `program`, `role`, `is_active` |
| `courses` | รายวิชา | `code`, `name_th`, `name_en`, `credits` |
| `schedule_entries` | ตารางเรียนรายบุคคล (1 แถว = 1 คาบเรียนต่อสัปดาห์) | `student_id`, `course_id`, `day_of_week` (0=จันทร์), `start_time`, `end_time`, `room_id` |
| `exam_entries` | ตารางสอบรายบุคคล | `student_id`, `course_id`, `exam_date`, `start_time`, `end_time`, `room_id`, `exam_type` (midterm/final) |
| `buildings` | อาคาร | `code`, `name_th`, `name_en`, `description` |
| `rooms` | ห้องภายในอาคาร | `building_id`, `room_number`, `floor`, `room_type` |
| `announcements` | ข่าวสาร/ประกาศของสาขา | `title`, `body`, `audience` (all/cs_student/staff), `created_at` |
| `access_logs` | ประวัติการใช้งานทุกครั้ง | `card_uid`, `card_holder_id`, `role`, `action`, `detail`, `granted`, `timestamp` |

`role` เป็น enum: `cs_student`, `other_student`, `staff`, `admin`, `guest` (guest คือค่า
default เมื่อไม่พบบัตรในระบบ หรือไม่ได้แตะบัตรเลย)

ข้อมูลตัวอย่างสำหรับสาธิตอยู่ใน `backend/app/seed.py` — รันด้วย `python -m app.seed` เพื่อ
เติมข้อมูลนักศึกษา/รายวิชา/ตารางเรียน/อาคาร/ประกาศตัวอย่างลงฐานข้อมูล SQLite

ข้อมูลความรู้สำหรับ AI Chatbot (ข้อมูลสาขา, อาคาร, FAQ) อยู่ที่
`backend/app/data/knowledge_base.json` แก้ไขไฟล์นี้เพื่ออัปเดตสิ่งที่ chatbot ตอบได้ โดยไม่ต้อง
แก้โค้ด
