# การติดตั้งฮาร์ดแวร์ (Raspberry Pi)

## รายการอุปกรณ์
- Raspberry Pi 4/5 (แนะนำ RAM 4GB ขึ้นไป)
- จอสัมผัส (Touch Screen) หรือจอมอนิเตอร์ + ทัชแพเนล USB
- เครื่องอ่านบัตร RFID/NFC แบบ USB HID keyboard-emulation (เช่น RDM6300 + ตัวแปลง USB, หรือ ACR122U)
- Raspberry Pi Camera Module หรือกล้อง USB (IP Camera สำรอง)
- MicroSD 32GB+, เคส, พัดลมระบายความร้อน

## เครื่องอ่านบัตร RFID/NFC

โค้ดนี้ออกแบบให้เครื่องอ่านทำงานแบบ **keyboard wedge**: เมื่อแตะบัตร เครื่องอ่านจะ "พิมพ์"
UID ของบัตรตามด้วยปุ่ม Enter ลงในช่อง input ที่ถูก focus ไว้อยู่แล้ว (ดู
`frontend/src/screens/CardScanScreen.jsx`) วิธีนี้ทำให้ไม่ต้องเขียนไดรเวอร์เฉพาะสำหรับ
เครื่องอ่านแต่ละรุ่น เสียบ USB แล้วใช้งานได้ทันที

ถ้าใช้เครื่องอ่านที่ต่อผ่าน UART/GPIO (เช่นโมดูล RC522 ต่อผ่าน SPI) ให้เขียนสคริปต์เสริมที่
อ่านค่า UID จากโมดูล แล้วจำลอง keyboard event (เช่นด้วยไลบรารี `evdev` หรือ `pyautogui`)
หรือจะยิง UID ตรงไปที่ `POST /api/cards/scan` จาก backend ก็ได้เช่นกัน

## กล้องตรวจจับผู้ใช้ (Camera Wake)

`backend/app/services/camera_wake.py` เปิดกล้องผ่าน OpenCV (`cv2.VideoCapture`) และรัน
Haar cascade face detection บน background thread ทุก ๆ ~0.3 วินาที เมื่อพบใบหน้าจะอัปเดต
สถานะ presence ที่ frontend polling อยู่ทุก 2 วินาทีผ่าน `GET /api/presence`

ตั้งค่า index ของกล้องและเวลาที่หน้าจอจะกลับไป idle ได้ที่ `.env`:

```
CAMERA_INDEX=0
CAMERA_IDLE_TIMEOUT_SECONDS=60
```

บน Raspberry Pi OS ต้องเปิดใช้งานกล้องก่อน (`sudo raspi-config` -> Interface Options ->
Camera) และติดตั้ง dependency ของ OpenCV เพิ่มเติม:

```bash
sudo apt install -y libatlas-base-dev libjasper-dev libqt4-test
```

ถ้าไม่มีกล้องต่ออยู่ (เช่นตอน dev บนเครื่อง Windows/Mac) ระบบจะ log คำเตือนแล้วปิดฟีเจอร์นี้
โดยอัตโนมัติ ไม่กระทบการทำงานส่วนอื่น — ผู้ใช้แตะหน้าจอเพื่อเริ่มใช้งานแทนได้เสมอ

## เข้าสู่ระบบอัตโนมัติด้วยใบหน้า (ไม่ต้องเลือก/แตะบัตร)

เมื่อใบหน้าอยู่นิ่งหน้ากล้องต่อเนื่องครบเวลาที่กำหนด (`FACE_STABLE_SECONDS`, ค่าเริ่มต้น 3
วินาที) ระบบจะเทียบใบหน้ากับข้อมูลที่ลงทะเบียนไว้ล่วงหน้า ถ้าตรงกันจะพาผู้ใช้เข้าหน้า
dashboard ตามสิทธิ์ทันที และเริ่มสนทนากับ AI ด้วยเสียงให้อัตโนมัติ โดยไม่ต้องแตะบัตรหรือเลือก
อะไรเลย

### ลงทะเบียนใบหน้าล่วงหน้า

ต้องมี `CardHolder` ในฐานข้อมูลอยู่ก่อนแล้ว (เช่นจาก `python -m app.seed` หรือเพิ่มเองผ่าน
ฐานข้อมูล) จากนั้นรันที่เครื่อง kiosk ที่มีกล้องต่ออยู่:

```bash
cd backend
python -m app.enroll_face 04A1B2C3          # ใช้ card_uid ของคนที่จะลงทะเบียน
# หรือกำหนดจำนวนภาพเอง
python -m app.enroll_face 04A1B2C3 --samples 30
```

สคริปต์จะเปิดหน้าต่างกล้อง ให้ขยับศีรษะเล็กน้อยระหว่างถ่ายเพื่อความแม่นยำ เก็บภาพครบแล้ว
จะฝึกโมเดล (`app/data/face_model.yml`) ให้อัตโนมัติ ทำซ้ำขั้นตอนนี้กับทุกคนที่ต้องการให้เข้า
ระบบด้วยใบหน้าได้ — ถ้ายังไม่มีใครลงทะเบียนเลย ฟีเจอร์นี้จะปิดตัวเองโดยอัตโนมัติและใช้การแตะ
บัตร/แตะหน้าจอแทน

ปรับความเข้มงวดของการจับคู่ได้ที่ `.env`:

```
FACE_RECOGNITION_ENABLED=true
FACE_STABLE_SECONDS=3.0
FACE_CONFIDENCE_THRESHOLD=80.0   # LBPH: ค่ายิ่งต่ำ = ยิ่งมั่นใจว่าตรงกัน
```

### ทดสอบโดยไม่มีกล้อง/ไม่มีใบหน้าลงทะเบียนจริง

หน้าจอ idle ของ frontend มีปุ่มโหมดทดสอบที่เรียก `POST /api/presence/simulate-recognition`
จำลองว่าจดจำใบหน้าของบัตรตัวอย่างได้แล้ว ใช้ทดสอบการ auto-login + เริ่มสนทนาด้วยเสียงได้ครบ
flow โดยไม่ต้องมีฮาร์ดแวร์จริง

## สนทนาด้วยเสียง (Voice Chat)

Chatbot รองรับการพูดคุยด้วยเสียงผ่าน Web Speech API ของเบราว์เซอร์ (ไม่ต้องติดตั้งอะไรเพิ่มที่
backend): `SpeechRecognition` ถอดเสียงภาษาไทย (`lang="th-TH"`) เป็นข้อความส่งไปที่ `/api/chat`
แล้ว `speechSynthesis` พูดคำตอบกลับ เมื่อเข้าสู่ระบบด้วยใบหน้า ระบบจะทักทายและเริ่มฟังคำถามให้
อัตโนมัติทันที ผู้ใช้ที่แตะบัตรเข้ามาก็กดปุ่ม "เริ่มสนทนาด้วยเสียง" ในหน้า chatbot เพื่อสลับมาใช้
เสียงเองได้เช่นกัน

ต้องใช้เบราว์เซอร์ที่รองรับ `webkitSpeechRecognition` (Chromium/Chrome) — แนะนำให้ kiosk รัน
Chromium ตามที่ตั้งค่าไว้ด้านล่าง ถ้าเบราว์เซอร์ไม่รองรับ ระบบจะซ่อนปุ่มเสียงและใช้พิมพ์คำถาม
แทนโดยอัตโนมัติ ต้องมีไมโครโฟนและลำโพงต่อกับ Raspberry Pi (USB หรือผ่านจอที่มีลำโพงในตัว)

## การรันเป็นแอปเต็มจอ (kiosk mode) บน Raspberry Pi OS

1. ตั้งค่า Raspberry Pi ให้ auto-login เข้า desktop
2. ติดตั้ง Chromium แล้วสร้าง autostart entry ที่รันด้วยแฟล็ก kiosk:
   ```bash
   chromium-browser --kiosk --incognito --noerrdialogs --disable-infobars http://localhost:5173
   ```
3. ใช้ `systemd` service หรือ `pm2` เพื่อให้ backend (`uvicorn`) และ frontend build
   (`npm run build` + `vite preview` หรือเสิร์ฟผ่าน nginx) เริ่มทำงานอัตโนมัติเมื่อบูตเครื่อง
