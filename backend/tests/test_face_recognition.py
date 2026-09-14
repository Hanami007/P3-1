"""Exercises the LBPH enroll/train/recognize pipeline with synthetic
images, since this environment has no physical camera to capture real
faces from. Two distinct synthetic "identities" (different geometric
patterns) stand in for two different people's faces.
"""

import numpy as np
import pytest

from app.services import face_recognition as face_recognition_service


def _synthetic_face(seed: int, noise: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed * 1000 + noise)
    base = np.zeros((200, 200), dtype=np.uint8)
    # A distinct geometric pattern per identity so LBPH has real texture
    # to key off, plus small per-sample noise so training sees variation.
    cv2_pattern = seed
    base[:: cv2_pattern + 2, :] = 200
    base[:, :: cv2_pattern + 3] = 150
    jitter = rng.integers(0, 15, size=base.shape, dtype=np.uint8)
    return np.clip(base.astype(int) + jitter, 0, 255).astype(np.uint8)


@pytest.fixture()
def isolated_face_dirs(tmp_path, monkeypatch):
    faces_dir = tmp_path / "faces"
    model_path = tmp_path / "face_model.yml"
    labels_path = tmp_path / "face_labels.json"
    monkeypatch.setattr(face_recognition_service, "FACES_DIR", faces_dir)
    monkeypatch.setattr(face_recognition_service, "MODEL_PATH", model_path)
    monkeypatch.setattr(face_recognition_service, "LABELS_PATH", labels_path)
    face_recognition_service._recognizer = None
    face_recognition_service._label_to_uid = {}
    yield faces_dir


def test_recognize_before_training_returns_none(isolated_face_dirs):
    card_uid, confidence = face_recognition_service.recognize(_synthetic_face(1), confidence_threshold=80.0)
    assert card_uid is None
    assert confidence == float("inf")


def test_train_and_recognize_distinguishes_identities(isolated_face_dirs):
    for i in range(15):
        face_recognition_service.save_face_sample("CARD_A", _synthetic_face(1, noise=i))
        face_recognition_service.save_face_sample("CARD_B", _synthetic_face(2, noise=i))

    assert sorted(face_recognition_service.enrolled_card_uids()) == ["CARD_A", "CARD_B"]
    assert face_recognition_service.train() is True

    uid_a, conf_a = face_recognition_service.recognize(_synthetic_face(1, noise=99), confidence_threshold=80.0)
    assert uid_a == "CARD_A"

    uid_b, conf_b = face_recognition_service.recognize(_synthetic_face(2, noise=99), confidence_threshold=80.0)
    assert uid_b == "CARD_B"


def test_train_with_no_enrolled_faces_returns_false(isolated_face_dirs):
    assert face_recognition_service.train() is False
