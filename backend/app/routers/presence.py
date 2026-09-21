import time
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services import camera_wake

router = APIRouter(prefix="/api/presence", tags=["presence"])


@router.get("/camera-feed")
def camera_feed():
    """Streams live camera frames as MJPEG for display on the kiosk UI."""
    def frame_generator():
        while True:
            frame_bytes = camera_wake.get_latest_frame_jpeg()
            if frame_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
            time.sleep(0.08)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("")
def get_presence():
    state = camera_wake.get_state()
    payload = {
        "awake": state.awake,
        "camera_available": state.camera_available,
        "last_seen": state.last_seen,
        "recognized_card_uid": state.recognized_card_uid,
    }
    if state.recognized_card_uid:
        # The frontend acts on this immediately (auto card-scan + login), so
        # don't keep handing out the same recognition on every poll while
        # that person is still standing in front of the camera.
        camera_wake.consume_recognition()
    return payload


@router.post("/simulate")
def simulate_presence():
    """Dev/demo helper: mark presence detected without a real camera
    (e.g. a hardware button or test script standing in for the sensor)."""
    camera_wake.mark_seen()
    return {"awake": True, "last_seen": datetime.utcnow()}


class SimulateRecognitionRequest(BaseModel):
    card_uid: str


@router.post("/simulate-recognition")
def simulate_recognition(payload: SimulateRecognitionRequest):
    """Dev/demo helper: pretend the camera just recognized this card_uid's
    enrolled face, for testing the hands-free login + voice flow without
    real hardware or enrolled face images."""
    camera_wake.simulate_recognition(payload.card_uid)
    return {"recognized_card_uid": payload.card_uid}
