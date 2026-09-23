def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_scan_known_card(client):
    resp = client.post("/api/cards/scan", json={"card_uid": "STUDENT1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["recognized"] is True
    assert body["role"] == "cs_student"


def test_scan_unknown_card_is_guest(client):
    resp = client.post("/api/cards/scan", json={"card_uid": "NOPE"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["recognized"] is False
    assert body["role"] == "guest"


def test_cs_student_can_view_own_schedule(client):
    resp = client.get("/api/students/STUDENT1/schedule", headers={"X-Card-UID": "STUDENT1"})
    assert resp.status_code == 200


def test_cs_student_cannot_view_others_schedule(client):
    resp = client.get("/api/students/OTHER/schedule", headers={"X-Card-UID": "STUDENT1"})
    assert resp.status_code in (403, 404)


def test_guest_cannot_view_schedule(client):
    resp = client.get("/api/students/STUDENT1/schedule")
    assert resp.status_code == 403


def test_buildings_open_to_guests(client):
    resp = client.get("/api/buildings")
    assert resp.status_code == 200


def test_logs_require_staff(client):
    assert client.get("/api/logs").status_code == 403
    assert client.get("/api/logs", headers={"X-Card-UID": "STUDENT1"}).status_code == 403
    assert client.get("/api/logs", headers={"X-Card-UID": "STAFF1"}).status_code == 200


def test_presence_endpoint(client):
    resp = client.get("/api/presence")
    assert resp.status_code == 200
    assert "awake" in resp.json()


def test_simulated_face_recognition_is_reported_once(client):
    resp = client.post("/api/presence/simulate-recognition", json={"card_uid": "STUDENT1"})
    assert resp.status_code == 200

    first = client.get("/api/presence").json()
    assert first["recognized_card_uid"] == "STUDENT1"

    second = client.get("/api/presence").json()
    assert second["recognized_card_uid"] is None


def test_rfid_tap_is_reported_once(client):
    resp = client.post("/api/presence/rfid-tap", json={"card_uid": "STUDENT1"})
    assert resp.status_code == 200

    first = client.get("/api/presence").json()
    assert first["recognized_card_uid"] == "STUDENT1"

    second = client.get("/api/presence").json()
    assert second["recognized_card_uid"] is None


def test_get_live_status_endpoint(client):
    resp = client.get("/api/students/STUDENT1/live-status", headers={"X-Card-UID": "STUDENT1"})
    assert resp.status_code == 200
    data = resp.json()
    assert "has_schedule" in data
    assert "status" in data
    assert "smart_greeting" in data
