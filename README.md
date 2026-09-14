# Smart Kiosk with Card-Based Identity and AI Assistant
### สาขาวิชาวิทยาการคอมพิวเตอร์ มหาวิทยาลัยแม่โจ้

ตู้คีออสก์อัจฉริยะที่แยกประเภทผู้ใช้ด้วยบัตรนักศึกษา (RFID/NFC) **หรือใบหน้า** โดยไม่ต้อง
ล็อกอิน — จ้องกล้องนิ่ง ๆ 3 วินาที ระบบจดจำใบหน้าแล้วพาเข้าสู่ระบบให้อัตโนมัติ พร้อมเริ่ม
สนทนากับ AI ด้วยเสียงทันที (ถาม-ตอบด้วยเสียงพูด ไม่ต้องพิมพ์) แสดงตารางเรียน/ตารางสอบเฉพาะ
บุคคลสำหรับนักศึกษาวิทคอม ให้บริการ AI Chatbot ตอบคำถามข้อมูลสาขาและอาคาร/สถานที่สำหรับ
ทุกคน พร้อมบันทึกประวัติการใช้งานและกำหนดสิทธิ์การเข้าถึงตามประเภทผู้ใช้

ดูรายละเอียดสถาปัตยกรรมที่ [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), การติดตั้งฮาร์ดแวร์ที่
[`docs/HARDWARE_SETUP.md`](docs/HARDWARE_SETUP.md) และโครงสร้างข้อมูลที่
[`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md)

## โครงสร้างโปรเจค

```
backend/    FastAPI + SQLite -- API, RBAC, chatbot, camera-wake, access logs
frontend/   React (Vite) -- kiosk touch UI
docs/       สถาปัตยกรรม, การติดตั้งฮาร์ดแวร์, โครงสร้างข้อมูล
```

## เริ่มต้นใช้งาน (Development)

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

copy .env.example .env        # Windows; cp บน macOS/Linux
# ค่าเริ่มต้นใช้ LLM_PROVIDER=gemini -- ขอ API key ฟรีที่ https://aistudio.google.com/apikey
# แล้วใส่ใน GEMINI_API_KEY= (หรือสลับเป็น claude / ollama ก็ได้)

python -m app.seed             # เติมข้อมูลตัวอย่าง (นักศึกษา/รายวิชา/อาคาร/ประกาศ)
python -m uvicorn app.main:app --reload --port 8000
```

API จะรันที่ `http://localhost:8000` (ดู Swagger UI ที่ `http://localhost:8000/docs`)

รันเทสต์: `python -m pytest` (จากโฟลเดอร์ `backend/`)

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

เปิด `http://localhost:5173` — Vite proxy คำขอ `/api/*` ไปยัง backend ที่ port 8000 ให้อัตโนมัติ
(ตั้งค่าที่ `frontend/vite.config.js`)

### ทดสอบโดยไม่มีเครื่องอ่านบัตร/กล้อง/ไมโครโฟนจริง

- หน้าจอ idle มีปุ่ม **โหมดทดสอบ** ให้กด "จำลองว่าจดจำใบหน้าได้แล้ว" สำหรับบัตรตัวอย่าง 3 แบบ
  ซึ่งจะพาเข้าสู่ระบบและเริ่มสนทนาด้วยเสียงทันที เสมือนกล้องจดจำใบหน้าจริง (เรียก
  `POST /api/presence/simulate-recognition` เบื้องหลัง)
- หน้าจอ "แตะบัตรเพื่อเข้าสู่ระบบ" ก็มีปุ่มเลือกบัตรจำลอง 3 แบบเช่นกัน (เข้าระบบแบบพิมพ์คุย
  กับ chatbot ได้ตามปกติ ไม่ auto-start เสียง)
- ถ้าไม่มีกล้องต่ออยู่ หน้าจอ idle จะ fallback เป็นการแตะหน้าจอ; ถ้าเบราว์เซอร์ไม่รองรับ
  Web Speech API หน้าแชทจะซ่อนปุ่มเสียงและใช้พิมพ์คำถามแทนโดยอัตโนมัติ

ใช้งานได้ครบทุกฟีเจอร์แม้กำลังพัฒนาบนเครื่อง PC ทั่วไปที่ไม่มีฮาร์ดแวร์จริง ส่วนการลงทะเบียน
ใบหน้าจริงและตั้งค่ากล้อง/ไมค์บน Raspberry Pi ดูที่
[`docs/HARDWARE_SETUP.md`](docs/HARDWARE_SETUP.md)

บัตรตัวอย่างจาก `backend/app/seed.py`:

| Card UID | บทบาท |
|---|---|
| `04A1B2C3` | นักศึกษาวิทคอม (รหัส 6604101335) |
| `04112233` | นักศึกษาสาขาอื่น |
| `04D4E5F6` | เจ้าหน้าที่สาขา |

## สิทธิ์การเข้าถึงตามประเภทผู้ใช้

| ฟีเจอร์ | นศ. วิทคอม | นศ. สาขาอื่น/ผู้เยี่ยมชม | เจ้าหน้าที่/admin |
|---|:---:|:---:|:---:|
| ตารางเรียน/ตารางสอบของตนเอง | ✅ | ❌ | ✅ (ทุกคน) |
| ค้นหาอาคาร/ห้อง | ✅ | ✅ | ✅ |
| AI Chatbot | ✅ | ✅ | ✅ |
| ประวัติการใช้งาน (Log) | ❌ | ❌ | ✅ |

## Hardware ที่รองรับ

Raspberry Pi 4/5, จอสัมผัส, เครื่องอ่าน RFID/NFC (USB HID), Pi Camera / IP Camera สำรอง —
รายละเอียดการต่อและตั้งค่าอยู่ที่ [`docs/HARDWARE_SETUP.md`](docs/HARDWARE_SETUP.md)
