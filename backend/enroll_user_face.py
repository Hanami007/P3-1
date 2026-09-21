import sys
import cv2
import numpy as np
from pathlib import Path

# Ensure utf-8 output
sys.stdout.reconfigure(encoding="utf-8")

from app.database import SessionLocal
from app.models import CardHolder, Role
from app.services import face_recognition

db = SessionLocal()
holder = (
    db.query(CardHolder)
    .filter((CardHolder.card_uid == "04A1B2C3") | (CardHolder.student_id == "6604101335"))
    .first()
)

if holder:
    holder.full_name = "ธราเทพ จันทร์ดำ"
    holder.student_id = "6604101335"
    holder.card_uid = "04A1B2C3"
    holder.role = Role.CS_STUDENT
    db.commit()
    print("Updated CardHolder: ธราเทพ จันทร์ดำ (6604101335)")
else:
    holder = CardHolder(
        card_uid="04A1B2C3",
        student_id="6604101335",
        full_name="ธราเทพ จันทร์ดำ",
        program="วิทยาการคอมพิวเตอร์",
        role=Role.CS_STUDENT,
        is_active=True,
    )
    db.add(holder)
    db.commit()
    print("Created CardHolder: ธราเทพ จันทร์ดำ (6604101335)")

db.close()

card_uid = "04A1B2C3"
person_dir = face_recognition.FACES_DIR / card_uid
person_dir.mkdir(parents=True, exist_ok=True)

# Clear old samples
for f in person_dir.glob("*.jpg"):
    f.unlink()

img_paths = [
    r"C:\Users\bass2\.gemini\antigravity\brain\4d3872c6-626c-491d-b885-cfb6ea23d127\.user_uploaded\media_1789980257063.jpg",
    r"C:\Users\bass2\.gemini\antigravity\brain\4d3872c6-626c-491d-b885-cfb6ea23d127\.user_uploaded\media_1789980257064.jpg",
    r"C:\Users\bass2\.gemini\antigravity\brain\4d3872c6-626c-491d-b885-cfb6ea23d127\.user_uploaded\media_1789980257082.jpg",
]

cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

saved_count = 0
for idx, p in enumerate(img_paths):
    img = cv2.imread(p)
    if img is None:
        continue
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(100, 100))
    if len(faces) == 0:
        continue
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face_crop = gray[y : y + h, x : x + w]
    face_resized = cv2.resize(face_crop, face_recognition.FACE_SIZE)

    # 1. Original
    face_recognition.save_face_sample(card_uid, face_resized)
    saved_count += 1

    # 2. Rotations (-6, -3, 3, 6 deg)
    h_r, w_r = face_resized.shape
    center = (w_r // 2, h_r // 2)
    for angle in [-6, -3, 3, 6]:
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(face_resized, M, (w_r, h_r))
        face_recognition.save_face_sample(card_uid, rotated)
        saved_count += 1

    # 3. Brightness variations
    for alpha in [0.85, 1.15]:
        adjusted = np.clip(face_resized.astype(float) * alpha, 0, 255).astype(np.uint8)
        face_recognition.save_face_sample(card_uid, adjusted)
        saved_count += 1

    # 4. Slight horizontal flip
    flipped = cv2.flip(face_resized, 1)
    face_recognition.save_face_sample(card_uid, flipped)
    saved_count += 1

print(f"Total enrolled face samples saved: {saved_count}")

# Train the model
trained = face_recognition.train()
print(f"Model training result: {trained}")

# Test recognition on the 3 original images
for idx, p in enumerate(img_paths):
    img = cv2.imread(p)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(100, 100))
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    predicted_uid, conf = face_recognition.recognize(gray[y : y + h, x : x + w], confidence_threshold=120.0)
    print(f"Verification image {idx}: recognized_uid={predicted_uid}, distance_score={conf:.1f}")
