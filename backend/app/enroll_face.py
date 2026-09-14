"""Enroll a person's face for hands-free kiosk login.

Opens the kiosk camera, captures ~20 face samples of the given card UID
(move your head slightly between captures for a more robust model), saves
them under app/data/faces/<card_uid>/, then retrains the recognition model.

Usage:
    python -m app.enroll_face 04A1B2C3
    python -m app.enroll_face 04A1B2C3 --samples 30
"""

import argparse
import time

import cv2

from app.config import settings
from app.services import face_recognition


def run(card_uid: str, target_samples: int):
    capture = cv2.VideoCapture(settings.camera_index)
    if not capture.isOpened():
        print(f"ไม่พบกล้องที่ index {settings.camera_index}")
        return

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    print(f"กำลังเก็บภาพใบหน้าสำหรับบัตร {card_uid} (เป้าหมาย {target_samples} ภาพ)")
    print("ขยับศีรษะเล็กน้อยระหว่างการถ่าย กด 'q' เพื่อยกเลิก")

    saved = 0
    last_capture = 0.0
    try:
        while saved < target_samples:
            ok, frame = capture.read()
            if not ok:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))

            for x, y, w, h in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            now = time.time()
            if len(faces) == 1 and now - last_capture > 0.4:
                x, y, w, h = faces[0]
                face_recognition.save_face_sample(card_uid, gray[y : y + h, x : x + w])
                saved += 1
                last_capture = now
                print(f"เก็บภาพแล้ว {saved}/{target_samples}")

            cv2.putText(frame, f"{saved}/{target_samples}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Enroll Face - press q to cancel", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()

    if saved == 0:
        print("ไม่ได้เก็บภาพใด ๆ ยกเลิกการลงทะเบียน")
        return

    print("กำลังฝึกโมเดลจดจำใบหน้า...")
    face_recognition.train()
    print("เสร็จสิ้น")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("card_uid", help="Card UID to associate this face with (must exist in card_holders)")
    parser.add_argument("--samples", type=int, default=20, help="Number of face images to capture")
    args = parser.parse_args()
    run(args.card_uid, args.samples)
