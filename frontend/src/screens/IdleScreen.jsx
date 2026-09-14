import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, roleToPath } from "../api";

const DEMO_CARDS = [
  { uid: "04A1B2C3", label: "นักศึกษาวิทคอม (demo)" },
  { uid: "04112233", label: "นักศึกษาสาขาอื่น (demo)" },
  { uid: "04D4E5F6", label: "เจ้าหน้าที่สาขา (demo)" },
];

export default function IdleScreen({ onSession }) {
  const navigate = useNavigate();
  const [presenceError, setPresenceError] = useState(false);
  const [status, setStatus] = useState("");

  const handledRef = useRef(false);
  const wokeToScanRef = useRef(false);

  useEffect(() => {
    const id = setInterval(async () => {
      if (handledRef.current) return;
      try {
        const state = await api.getPresence();
        setPresenceError(false);

        if (state.recognized_card_uid) {
          handledRef.current = true;
          setStatus("จดจำใบหน้าได้ กำลังเข้าสู่ระบบ...");
          try {
            const result = await api.scanCard(state.recognized_card_uid);
            onSession({
              cardUid: state.recognized_card_uid,
              holder: result.holder,
              role: result.role,
              via: "face",
            });
            navigate(roleToPath(result.role));
          } catch (err) {
            setStatus(`เข้าสู่ระบบไม่สำเร็จ: ${err.message}`);
            handledRef.current = false;
          }
          return;
        }

        if (state.awake && !wokeToScanRef.current) {
          wokeToScanRef.current = true;
          navigate("/scan");
        }
      } catch {
        setPresenceError(true);
      }
    }, 1500);
    return () => clearInterval(id);
  }, [navigate, onSession]);

  return (
    <div className="idle-screen" onClick={() => navigate("/scan")}>
      <div className="pulse">🎓</div>
      <h1>Smart Kiosk สาขาวิทยาการคอมพิวเตอร์</h1>
      <p>ระบบจะจดจำใบหน้าและเข้าสู่ระบบให้อัตโนมัติ (จ้องกล้องนิ่ง ๆ ประมาณ 3 วินาที)</p>
      <p>หรือแตะบัตร/แตะหน้าจอเพื่อเข้าใช้งานด้วยตนเอง</p>
      {status && <p>{status}</p>}
      {presenceError && <p className="error-text">ไม่สามารถเชื่อมต่อกล้องตรวจจับผู้ใช้ได้ ใช้การแตะหน้าจอ/บัตรแทนได้</p>}

      <div
        className="card"
        style={{ marginTop: 40, maxWidth: 480 }}
        onClick={(e) => e.stopPropagation()}
      >
        <p style={{ color: "var(--muted)", marginTop: 0 }}>
          โหมดทดสอบ (ไม่มีกล้อง/ใบหน้าที่ลงทะเบียนจริง): จำลองว่าจดจำใบหน้าได้แล้ว
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "center" }}>
          {DEMO_CARDS.map((c) => (
            <button
              key={c.uid}
              className="btn secondary"
              onClick={() => api.simulateFaceRecognition(c.uid)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
