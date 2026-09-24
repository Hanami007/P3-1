# สถาปัตยกรรมระบบ (Architecture)

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│   RFID/NFC Reader (USB HID)  │        │   Pi Camera / IP Camera       │
│   -> types card UID + Enter  │        │   -> OpenCV face detect + LBPH │
│                               │        │      recognition (auto-login) │
└──────────────┬───────────────┘        └───────────────┬───────────────┘
               │ keyboard-wedge input                    │ background thread
               ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Frontend (React, kiosk touch UI)                  │
│  IdleScreen -> CardScanScreen -> StudentDashboard / GuestKiosk /      │
│                                   AdminLogs (staff/admin)             │
└───────────────────────────────┬───────────────────────────────────────┘
                                 │ REST (fetch, /api/* via Vite proxy)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                                  │
│  routers/  cards · schedule · buildings · announcements · chatbot ·   │
│            logs · presence                                            │
│  services/ llm (Claude API / Ollama) · camera_wake (OpenCV thread)     │
│  permissions.py  -> role resolved fresh from the card UID on every     │
│                     request (no login session; the card IS the auth)  │
└───────────────────────────────┬───────────────────────────────────────┘
                                 ▼
                    SQLite (kiosk.db, swappable for MySQL
                    via DATABASE_URL for a larger deployment)
```

## หลักการออกแบบที่สำคัญ

1. **ไม่มีการล็อกอิน (no login session).** บัตร RFID/NFC ที่แตะคือหลักฐานยืนยันตัวตน
   ทุก endpoint ที่ต้องการสิทธิ์จะ resolve role ใหม่จาก UID ของบัตรที่ส่งมาใน header
   `X-Card-UID` ทุกครั้ง (ดู `backend/app/permissions.py`) — ถ้าเจ้าหน้าที่ปิดใช้งานบัตร
   ในฐานข้อมูล สิทธิ์จะถูกตัดทันทีในคำขอถัดไป โดยไม่ต้องมีระบบ token/JWT
2. **แยกสิทธิ์ตามประเภทผู้ใช้ (RBAC).**
   - `cs_student` — ดูตารางเรียน/ตารางสอบของตนเอง, chatbot, อาคาร/ห้อง
   - `other_student` / `guest` — ค้นหาอาคาร/ห้อง, chatbot (ไม่เห็นตารางเรียน)
   - `staff` / `admin` — ดู log การใช้งานทั้งหมด, ดูตารางเรียนของทุกคน
3. **กล้องปลุกหน้าจอ + เข้าสู่ระบบอัตโนมัติด้วยใบหน้า** ทำงานแยกจาก request/response หลัก
   เป็น background thread เดียว (`camera_wake.py`) ที่:
   - พบใบหน้า -> ปลุกหน้าจอทันที (`awake=true`)
   - ใบหน้าเดิมอยู่นิ่งต่อเนื่องครบ `FACE_STABLE_SECONDS` (ค่าเริ่มต้น 3 วินาที) -> ส่งภาพใบหน้า
     ไปเทียบกับโมเดลที่ฝึกไว้ (`face_recognition.py`, LBPH ผ่าน `cv2.face` — เลือกเพราะติดตั้งเป็น
     wheel ธรรมดาได้ทั้งบน Windows และ Raspberry Pi โดยไม่ต้องคอมไพล์ ต่างจาก dlib/face_recognition)
   - จับคู่ได้ -> เผยแพร่ `recognized_card_uid` ให้ frontend อ่านผ่าน `GET /api/presence`
     (poll ทุก ~1.5-2 วินาที) แล้ว frontend เรียก `/api/cards/scan` ให้เองทันที **โดยผู้ใช้ไม่ต้อง
     เลือกอะไรเลย** — ข้าม `CardScanScreen` ไปเข้าหน้า dashboard ตามสิทธิ์โดยตรง
   - แต่ละ recognition ถูกส่งให้ frontend ครั้งเดียว (`consume_recognition()`) เพื่อไม่ให้ auto-login
     ซ้ำทุก poll ขณะที่คนคนเดิมยังยืนอยู่หน้ากล้อง และจะรีเซ็ตเมื่อใบหน้าหายไปจากเฟรมนานพอ
     (ให้คนถัดไปถูกจดจำเป็นคนใหม่)
   - ลงทะเบียนใบหน้าล่วงหน้าด้วย `python -m app.enroll_face <card_uid>` (ดูรายละเอียดที่
     [`HARDWARE_SETUP.md`](HARDWARE_SETUP.md)) ถ้ายังไม่มีใครลงทะเบียน ระบบจะปิดการจดจำใบหน้า
     โดยอัตโนมัติและ fallback เป็นแตะบัตร/แตะหน้าจอแทน ไม่ error
4. **Chatbot เป็น retrieval แบบง่าย (system-prompt grounding) และคุยด้วยเสียงได้.** ข้อมูล
   สาขา/บุคลากร/อาคาร/ห้อง/ช่องทางติดต่อเมื่อมีปัญหา อ่านสดจากฐานข้อมูล
   (`backend/app/services/knowledge.py`) และฝังลง system prompt ทุกครั้งที่เรียก LLM สลับ provider ได้ระหว่าง Gemini API (ฟรี), Claude API, หรือ Ollama
   (local) ผ่าน `LLM_PROVIDER` ใน `.env` — ฝั่ง frontend ใช้ Web Speech API ของเบราว์เซอร์
   (`SpeechRecognition` ถอดเสียงเป็นข้อความ, `speechSynthesis` พูดคำตอบกลับ) ทำงานล้วน ๆ ใน
   เบราว์เซอร์โดยไม่ต้องมี backend เพิ่ม เมื่อเข้าสู่ระบบด้วยการจดจำใบหน้า ระบบจะเริ่มสนทนาด้วย
   เสียงให้อัตโนมัติทันที (ทักทายด้วยเสียง แล้วเริ่มฟังคำถามต่อเนื่อง) ส่วนกรณีแตะบัตร/เข้าแบบ
   ผู้เยี่ยมชมยังใช้พิมพ์คำถามได้ตามปกติ หรือกดปุ่ม "เริ่มสนทนาด้วยเสียง" เพื่อสลับมาใช้เสียงเอง
   ถ้าเบราว์เซอร์ไม่รองรับ (เช่นไม่ใช่ Chromium) จะ fallback เป็นพิมพ์ข้อความโดยอัตโนมัติ
5. **บันทึกทุกการใช้งานลง `access_logs`** (แตะบัตร/จดจำใบหน้า, ดูตาราง, คุยกับ chatbot,
   ถูกปฏิเสธสิทธิ์) เพื่อให้เจ้าหน้าที่ตรวจสอบย้อนหลังได้ผ่านหน้า Log (เฉพาะ staff/admin)
