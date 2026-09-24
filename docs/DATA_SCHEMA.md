# โครงสร้างข้อมูล (Data Schema)

ตารางทั้งหมดกำหนดไว้ที่ `backend/app/models.py` (SQLAlchemy ORM, ใช้ได้ทั้ง SQLite และ MySQL
โดยเปลี่ยนแค่ `DATABASE_URL`) ค่าเริ่มต้นคือไฟล์ `backend/kiosk.db` (path แบบเต็ม ไม่ขึ้นกับโฟลเดอร์ที่รัน)

## ข้อมูลสาธารณะ (ทุกคนดูได้ และ AI ใช้ตอบคำถาม)

| ตาราง | คำอธิบาย | ฟิลด์สำคัญ |
|---|---|---|
| `department_info` | ข้อมูลสาขา (1 แถว) | `name_th`, `address`, `phone`, `email`, `facebook`, `line`, `website`, `office_hours` |
| `personnels` | อาจารย์และเจ้าหน้าที่ | `title`, `full_name`, `position` (lecturer/staff), `phone`, `email`, `room_id` |
| `buildings` | อาคาร (`code` = หมายเลขตึกของมหาวิทยาลัย เช่น `105`) | `code`, `name_th`, `name_en`, `short_name` (ชื่อที่นักศึกษาเรียก เช่น "ตึกวิท" — AI ใช้ตอนพูด), `description` |
| `rooms` | ห้องภายในอาคาร — unique (`building_id`, `room_number`) | `building_id`, `room_number`, `floor` (ว่างได้), `room_type` |
| `problem_contacts` | เมื่อมีปัญหาต้องไปที่ไหน | `topic`, `office`, `building_id` (ว่างได้), `location_note`, `phone`, `sort_order` |
| `announcements` | ข่าวสาร/ประกาศ (AI เห็นเฉพาะ `audience = all`) | `title`, `body`, `audience` (all/cs_student/staff), `created_at` |

## ข้อมูลนักศึกษา (เห็นเฉพาะเจ้าของบัตร)

| ตาราง | คำอธิบาย | ฟิลด์สำคัญ |
|---|---|---|
| `card_holders` | ผู้ถือบัตร (นักศึกษาวิทคอม/สาขาอื่น/บุคลากร) | `card_uid` (unique, ว่างได้จนกว่าจะอ่านบัตรจริง), `student_id`, `full_name`, `program`, `role`, `is_active`, `advisor_id` → `personnels` |
| `courses` | รายวิชา | `code`, `name_th`, `name_en`, `credits` |
| `course_sections` | กลุ่มเรียนของรายวิชาในแต่ละภาค | `course_id`, `section_no`, `term` (เช่น `1/2569`) |
| `enrollments` | นักศึกษาคนไหนลงกลุ่มเรียนไหน | `card_holder_id`, `section_id` |
| `schedule_entries` | คาบเรียนประจำสัปดาห์ของกลุ่มเรียน | `section_id`, `day_of_week` (0=จันทร์), `start_time`, `end_time`, `room_id` |
| `exam_entries` | สอบกลางภาค/ปลายภาคของกลุ่มเรียน | `section_id`, `exam_type` (midterm/final), `exam_date`, `start_time`, `end_time`, `room_id` — วันเวลาห้องว่างได้ (= ยังไม่ประกาศ) |

ตารางเรียน/สอบผูกกับ **กลุ่มเรียน** ไม่ใช่ตัวนักศึกษา นักศึกษาหลายคนที่เรียนกลุ่มเดียวกันจึงใช้ข้อมูลชุดเดียวกัน
ดึงตารางของนักศึกษาหนึ่งคนผ่าน `backend/app/services/student_data.py`

## อื่น ๆ

| ตาราง | คำอธิบาย | ฟิลด์สำคัญ |
|---|---|---|
| `access_logs` | ประวัติการใช้งานทุกครั้ง | `card_uid`, `card_holder_id`, `role`, `action`, `detail`, `granted`, `timestamp` |

`role` เป็น enum: `cs_student`, `other_student`, `staff`, `admin`, `guest` (guest คือค่า
default เมื่อไม่พบบัตรในระบบ หรือไม่ได้แตะบัตรเลย)

## ข้อมูลเริ่มต้นและ AI

ข้อมูลจริงของสาขา + นักศึกษาเดโมอยู่ใน `backend/app/seed.py` รันด้วย `python -m app.seed`
(รันซ้ำได้ จะเพิ่มเฉพาะแถวที่ยังไม่มี ไม่แก้แถวเดิม)

AI Chatbot อ่านข้อมูลสาธารณะจากฐานข้อมูลทุกครั้งที่มีคำถาม (`backend/app/services/knowledge.py`)
แก้ข้อมูลใน DB แล้ว chatbot ตอบตามข้อมูลใหม่ทันที ไม่ต้อง restart

ยังไม่มีระบบ migration (Alembic) — ถ้าเปลี่ยนโครงสร้างตาราง ให้ลบ `backend/kiosk.db` แล้วรัน seed ใหม่
