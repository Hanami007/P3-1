"""Face enrollment + recognition for hands-free kiosk login.

Uses OpenCV's built-in LBPH recognizer (``cv2.face``, from
opencv-contrib-python) rather than dlib/face_recognition: it installs as a
plain wheel on both Windows (dev) and Raspberry Pi OS with no C++ compiler
required, which matters a lot more for a student project than the extra
accuracy dlib would buy.

Enrolled face crops live under ``app/data/faces/<card_uid>/*.jpg`` (see
``app/enroll_face.py``). ``train()`` builds a single LBPH model from
whatever is enrolled and writes it to ``app/data/face_model.yml`` plus a
label map (``face_labels.json``) from the integer labels LBPH requires back
to card UIDs.
"""

import json
import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
FACES_DIR = DATA_DIR / "faces"
MODEL_PATH = DATA_DIR / "face_model.yml"
LABELS_PATH = DATA_DIR / "face_labels.json"
FACE_SIZE = (200, 200)

_recognizer = None
_label_to_uid: dict[int, str] = {}


def _load_label_map() -> dict[int, str]:
    if not LABELS_PATH.exists():
        return {}
    return {int(k): v for k, v in json.loads(LABELS_PATH.read_text(encoding="utf-8")).items()}


def _save_label_map(mapping: dict[int, str]):
    LABELS_PATH.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")


def enrolled_card_uids() -> list[str]:
    if not FACES_DIR.exists():
        return []
    return sorted(p.name for p in FACES_DIR.iterdir() if p.is_dir() and any(p.iterdir()))


def save_face_sample(card_uid: str, face_gray: np.ndarray) -> Path:
    """Save one already-cropped, grayscale face image for later training."""
    person_dir = FACES_DIR / card_uid
    person_dir.mkdir(parents=True, exist_ok=True)
    resized = cv2.resize(face_gray, FACE_SIZE)
    existing = list(person_dir.glob("*.jpg"))
    out_path = person_dir / f"{len(existing) + 1:03d}.jpg"
    cv2.imwrite(str(out_path), resized)
    return out_path


def train() -> bool:
    """Rebuild the LBPH model from every enrolled face sample on disk.

    Returns False (and leaves recognition disabled) if nobody is enrolled
    yet, so the rest of the app can degrade gracefully.
    """
    card_uids = enrolled_card_uids()
    if not card_uids:
        logger.info("No enrolled faces found; face recognition stays disabled")
        return False

    faces: list[np.ndarray] = []
    labels: list[int] = []
    label_map: dict[int, str] = {}

    for label, card_uid in enumerate(card_uids):
        label_map[label] = card_uid
        for image_path in (FACES_DIR / card_uid).glob("*.jpg"):
            img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            faces.append(cv2.resize(img, FACE_SIZE))
            labels.append(label)

    if not faces:
        logger.warning("Enrolled face folders exist but contain no readable images")
        return False

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    recognizer.write(str(MODEL_PATH))
    _save_label_map(label_map)

    global _recognizer, _label_to_uid
    _recognizer = recognizer
    _label_to_uid = label_map
    logger.info("Face model trained on %d identities (%d images)", len(card_uids), len(faces))
    return True


def _ensure_loaded() -> bool:
    global _recognizer, _label_to_uid
    if _recognizer is not None:
        return True
    if not MODEL_PATH.exists() or not LABELS_PATH.exists():
        return False
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(MODEL_PATH))
    _recognizer = recognizer
    _label_to_uid = _load_label_map()
    return True


def recognize(face_gray: np.ndarray, confidence_threshold: float) -> tuple[str | None, float]:
    """Predict which enrolled card_uid a cropped, grayscale face belongs to.

    LBPH confidence is a *distance* -- lower means a better match. Returns
    (None, confidence) when nothing is trained yet or the best match is
    still worse (higher) than confidence_threshold.
    """
    if not _ensure_loaded():
        return None, float("inf")

    resized = cv2.resize(face_gray, FACE_SIZE)
    label, confidence = _recognizer.predict(resized)
    if confidence > confidence_threshold:
        return None, confidence
    return _label_to_uid.get(label), confidence
