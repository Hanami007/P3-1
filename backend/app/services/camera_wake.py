"""Presence detection to auto-wake the kiosk screen, plus hands-free login.

Runs face detection on a background thread against the Pi Camera / USB
webcam. Any face wakes the screen immediately. If the *same* face then
holds steady in frame for ``settings.face_stable_seconds`` (default 3s),
it is matched against enrolled faces (see ``face_recognition.py``) and, on
a confident match, published as ``recognized_card_uid`` so the frontend can
log the person in with no card tap and no manual selection.

If no camera is attached (e.g. developing on a laptop without one),
detection simply never starts and the kiosk falls back to manual wake
(touch) / card tap -- the rest of the app keeps working either way.
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.config import settings
from app.services import face_recognition

logger = logging.getLogger(__name__)

# A face has to disappear for this long before we treat the next one that
# shows up as a *new* person (otherwise a recognized user glancing away for
# a frame would immediately be treated as freshly arrived).
_FACE_GONE_RESET_SECONDS = 2.0


@dataclass
class PresenceState:
    awake: bool = False
    last_seen: datetime | None = None
    camera_available: bool = False
    recognized_card_uid: str | None = None


_state = PresenceState()
_lock = threading.Lock()
_stop_event = threading.Event()
_thread: threading.Thread | None = None

_recognized_consumed = False
_face_first_seen: float | None = None
_face_last_seen: float | None = None
_latest_frame_jpeg: bytes | None = None


def get_latest_frame_jpeg() -> bytes | None:
    with _lock:
        return _latest_frame_jpeg


def get_state() -> PresenceState:
    with _lock:
        if _state.awake and _state.last_seen:
            idle_for = datetime.utcnow() - _state.last_seen
            if idle_for > timedelta(seconds=settings.camera_idle_timeout_seconds):
                _state.awake = False
        visible_uid = None if _recognized_consumed else _state.recognized_card_uid
        return PresenceState(
            awake=_state.awake,
            last_seen=_state.last_seen,
            camera_available=_state.camera_available,
            recognized_card_uid=visible_uid,
        )


def consume_recognition():
    """Call once the frontend has acted on a recognized_card_uid, so the
    same auto-login doesn't fire again on the next poll while that same
    person is still standing in front of the camera."""
    global _recognized_consumed
    with _lock:
        _recognized_consumed = True


def mark_seen():
    """Called by the detection loop, or manually via /api/presence/simulate
    for development environments without a physical camera."""
    with _lock:
        _state.awake = True
        _state.last_seen = datetime.utcnow()


def simulate_recognition(card_uid: str):
    """Dev/demo helper standing in for a real 3-second face match."""
    global _recognized_consumed
    with _lock:
        _state.awake = True
        _state.last_seen = datetime.utcnow()
        _state.recognized_card_uid = card_uid
        _recognized_consumed = False


def _on_face_detected():
    """Track how long a face has been continuously in frame and, once it
    passes the stability threshold, attempt recognition."""
    global _face_first_seen, _face_last_seen, _recognized_consumed
    now = time.monotonic()
    _face_last_seen = now
    if _face_first_seen is None:
        _face_first_seen = now


def _on_face_recognized(card_uid: str):
    global _recognized_consumed
    with _lock:
        if _state.recognized_card_uid != card_uid:
            _state.recognized_card_uid = card_uid
            _recognized_consumed = False


def _on_no_face():
    """Reset stability tracking once a face has been absent long enough
    that the next one should be treated as a new person."""
    global _face_first_seen, _face_last_seen
    now = time.monotonic()
    if _face_last_seen is not None and now - _face_last_seen > _FACE_GONE_RESET_SECONDS:
        _face_first_seen = None
        _face_last_seen = None
        with _lock:
            _state.recognized_card_uid = None


def _detection_loop():
    try:
        import cv2
    except ImportError:
        logger.warning("opencv not installed; camera wake disabled")
        return

    import sys
    capture = None
    if sys.platform == "win32":
        try:
            capture = cv2.VideoCapture(settings.camera_index, cv2.CAP_DSHOW)
        except Exception:
            pass
    if capture is None or not capture.isOpened():
        capture = cv2.VideoCapture(settings.camera_index)

    if not capture.isOpened():
        logger.warning("No camera found at index %s; camera wake disabled", settings.camera_index)
        with _lock:
            _state.camera_available = False
        return

    with _lock:
        _state.camera_available = True

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    logger.info("Camera wake detection started on index %s", settings.camera_index)

    global _latest_frame_jpeg

    try:
        while not _stop_event.is_set():
            ok, frame = capture.read()
            if not ok:
                time.sleep(0.5)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))

            display_frame = frame.copy()
            for (fx, fy, fw, fh) in faces:
                cv2.rectangle(display_frame, (fx, fy), (fx + fw, fy + fh), (59, 158, 255), 2)

            ret, encoded = cv2.imencode(".jpg", display_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ret:
                with _lock:
                    _latest_frame_jpeg = encoded.tobytes()

            if len(faces) > 0:
                mark_seen()
                _on_face_detected()

                if settings.face_recognition_enabled and _face_first_seen is not None:
                    stable_for = time.monotonic() - _face_first_seen
                    if stable_for >= settings.face_stable_seconds:
                        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                        card_uid, confidence = face_recognition.recognize(
                            gray[y : y + h, x : x + w], settings.face_confidence_threshold
                        )
                        if card_uid:
                            logger.info("Face recognized: %s (confidence %.1f)", card_uid, confidence)
                            _on_face_recognized(card_uid)
            else:
                _on_no_face()

            time.sleep(0.08)
    finally:
        capture.release()


def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_detection_loop, daemon=True)
    _thread.start()


def stop():
    _stop_event.set()
    if _thread:
        _thread.join(timeout=2)
