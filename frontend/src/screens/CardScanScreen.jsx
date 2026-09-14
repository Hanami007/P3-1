import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, roleToPath } from "../api";

const DEMO_CARDS = [
  { uid: "04A1B2C3", label: "นักศึกษาวิทคอม (demo)" },
  { uid: "04112233", label: "นักศึกษาสาขาอื่น (demo)" },
  { uid: "04D4E5F6", label: "เจ้าหน้าที่สาขา (demo)" },
];

export default function CardScanScreen({ onSession }) {
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [buffer, setBuffer] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function submitCard(uid) {
    if (!uid || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.scanCard(uid);
      onSession({ cardUid: uid, holder: result.holder, role: result.role, via: "card" });
      navigate(roleToPath(result.role));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      setBuffer("");
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") {
      submitCard(buffer.trim());
    }
  }

  return (
    <div className="idle-screen">
      <h1>แตะบัตรเพื่อเข้าสู่ระบบ</h1>
      <p>วางบัตรนักศึกษา/บัตรประจำตัวที่เครื่องอ่าน RFID/NFC</p>

      <input
        ref={inputRef}
        className="hidden-input"
        value={buffer}
        onChange={(e) => setBuffer(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => inputRef.current?.focus()}
        autoFocus
      />

      {error && <p className="error-text">{error}</p>}
      {busy && <p>กำลังตรวจสอบบัตร...</p>}

      <button className="btn secondary" onClick={() => navigate("/guest")}>
        เข้าใช้งานแบบผู้เยี่ยมชม (ไม่มีบัตร)
      </button>

      <div className="card" style={{ marginTop: 40, maxWidth: 480 }}>
        <p style={{ color: "var(--muted)", marginTop: 0 }}>โหมดทดสอบ (ไม่มีเครื่องอ่านบัตรจริง): เลือกบัตรจำลอง</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "center" }}>
          {DEMO_CARDS.map((c) => (
            <button key={c.uid} className="btn secondary" onClick={() => submitCard(c.uid)}>
              {c.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
