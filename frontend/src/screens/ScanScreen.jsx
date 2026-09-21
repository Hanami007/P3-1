import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, roleToPath } from "../api";
import { useAudioNoiseAnalyzer } from "../hooks/useAudioNoiseAnalyzer";

const DEMO_CARDS = [
  { uid: "04A1B2C3", label: "ธราเทพ จันทร์ดำ (6604101335)" },
  { uid: "04112233", label: "นักศึกษาสาขาอื่น" },
  { uid: "04D4E5F6", label: "เจ้าหน้าที่สาขา" },
];

const COPY = {
  idle: { title: "วางใบหน้าให้อยู่ในกรอบ", hint: "ระบบจะจดจำใบหน้าและเข้าสู่ระบบให้อัตโนมัติ หรือแตะบัตรนักศึกษา/บัตรประจำตัวที่เครื่องอ่าน" },
  scanning: { title: "กำลังสแกนใบหน้าและตรวจสอบเสียง...", hint: "กรุณาอยู่นิ่ง ๆ สักครู่" },
  recognized: { title: "จดจำใบหน้าได้แล้ว", hint: "กำลังเข้าสู่ระบบ..." },
  failed: { title: "เข้าสู่ระบบไม่สำเร็จ", hint: "" },
};

export default function ScanScreen({ onSession }) {
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [phase, setPhase] = useState("idle");
  const [hint, setHint] = useState(COPY.idle.hint);
  const [cameraError, setCameraError] = useState(false);
  const [buffer, setBuffer] = useState("");
  const [devOpen, setDevOpen] = useState(false);

  const handledRef = useRef(false);

  // Real-time audio noise & peak sound analyzer
  const {
    currentDb,
    ambientDb,
    peakDb,
    condition,
    isListening,
    simulateNoise,
  } = useAudioNoiseAnalyzer({ active: true });

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function loginWithCard(uid, via) {
    if (!uid || handledRef.current) return;
    handledRef.current = true;
    setPhase("recognized");
    setHint(COPY.recognized.hint);
    try {
      const result = await api.scanCard(uid, {
        ambient_noise_db: ambientDb,
        peak_noise_db: peakDb,
      });
      onSession({
        cardUid: uid,
        holder: result.holder,
        role: result.role,
        smartGreeting: result.smart_greeting,
        liveStatus: result.live_status,
        noiseData: { ambientDb, peakDb, condition },
        via,
      });
      navigate(roleToPath(result.role));
    } catch (err) {
      setPhase("failed");
      setHint(err.message);
      setTimeout(() => {
        handledRef.current = false;
        setPhase("idle");
        setHint(COPY.idle.hint);
      }, 2500);
    }
  }

  useEffect(() => {
    const id = setInterval(async () => {
      if (handledRef.current) return;
      try {
        const state = await api.getPresence();
        setCameraError(false);

        if (state.recognized_card_uid) {
          loginWithCard(state.recognized_card_uid, "face");
          return;
        }
        setPhase(state.awake ? "scanning" : "idle");
        setHint(state.awake ? COPY.scanning.hint : COPY.idle.hint);
      } catch {
        setCameraError(true);
      }
    }, 1200);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleCardKeyDown(e) {
    if (e.key === "Enter") {
      const uid = buffer.trim();
      setBuffer("");
      loginWithCard(uid, "card");
    }
  }

  const [cameraLive, setCameraLive] = useState(false);

  const title = phase === "failed" ? COPY.failed.title : COPY[phase].title;

  return (
    <div className="scan-screen">
      <input
        ref={inputRef}
        className="hidden-input"
        value={buffer}
        onChange={(e) => setBuffer(e.target.value)}
        onKeyDown={handleCardKeyDown}
        onBlur={() => inputRef.current?.focus()}
        autoFocus
      />

      <h1 className="scan-screen-title">Smart Kiosk สาขาวิทยาการคอมพิวเตอร์</h1>

      <div className={`scan-frame ${phase} ${cameraLive ? "has-video" : ""}`}>
        <span className="corner tl" />
        <span className="corner tr" />
        <span className="corner bl" />
        <span className="corner br" />
        <div className="scan-sweep" />

        <img
          src="/api/presence/camera-feed"
          alt="Live Camera"
          className="camera-stream-feed"
          onLoad={() => setCameraLive(true)}
          onError={() => setCameraLive(false)}
          style={{ display: cameraLive ? "block" : "none" }}
        />

        {!cameraLive && (
          <svg className="face-icon" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="8.5" r="4" />
            <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8Z" />
          </svg>
        )}
      </div>

      <div className="scan-status">
        <h2>{title}</h2>
        <p>{hint}</p>
      </div>

      {/* Real-time Audio Noise & Loudest Sound Monitor */}
      <div className={`noise-meter-card ${condition}`}>
        <div className="noise-header">
          <div className="noise-title-group">
            <span className={`noise-live-dot ${isListening ? "active" : ""}`} />
            <span className="noise-title">AI ตรวจสอบเสียงรบกวนรอบข้าง</span>
          </div>
          <span className={`noise-badge ${condition}`}>
            {condition === "quiet"
              ? "🟢 สภาพแวดล้อมเงียบ"
              : condition === "moderate"
              ? "🟡 เสียงรบกวนปานกลาง"
              : "🔴 เสียงรบกวนสูง"}
          </span>
        </div>

        <div className="noise-visualizer">
          <div className="noise-bar-container">
            <div
              className={`noise-bar-fill ${condition}`}
              style={{
                width: `${Math.min(100, Math.max(8, ((currentDb - 30) / 70) * 100))}%`,
              }}
            />
          </div>
        </div>

        <div className="noise-details">
          <div className="noise-stat">
            <span className="noise-label">เสียงขณะนี้</span>
            <span className="noise-value">{currentDb} dB</span>
          </div>
          <div className="noise-stat">
            <span className="noise-label">เสียงเฉลี่ยรอบข้าง</span>
            <span className="noise-value">{ambientDb} dB</span>
          </div>
          <div className="noise-stat highlight">
            <span className="noise-label">เสียงดังที่สุด (Peak)</span>
            <span className="noise-value peak">{peakDb} dB</span>
          </div>
        </div>
      </div>

      {cameraError && (
        <p className="error-text" style={{ fontSize: 14 }}>
          ไม่สามารถเชื่อมต่อกล้องได้ ใช้การแตะบัตรแทนได้
        </p>
      )}

      <div className="guest-divider">
        <span>สำหรับบุคคลภายนอก</span>
      </div>
      <button className="guest-btn" onClick={() => navigate("/guest")}>
        เข้าใช้งานแบบผู้เยี่ยมชม (ไม่มีบัตร/ใบหน้าลงทะเบียน)
      </button>

      <button className="dev-toggle" onClick={() => setDevOpen((v) => !v)} title="โหมดทดสอบ">
        ⚙
      </button>
      {devOpen && (
        <div className="dev-panel">
          <p style={{ margin: "0 0 8px" }}>โหมดทดสอบ: จำลองว่าจดจำใบหน้าได้แล้ว</p>
          {DEMO_CARDS.map((c) => (
            <button
              key={c.uid}
              className="btn secondary"
              onClick={() => api.simulateFaceRecognition(c.uid)}
            >
              {c.label}
            </button>
          ))}
          <p style={{ margin: "12px 0 6px", fontSize: 12, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
            จำลองระดับเสียงรอบข้าง:
          </p>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button
              className="btn secondary"
              style={{ fontSize: 11, padding: "4px 8px" }}
              onClick={() => simulateNoise(38, 44)}
            >
              เงียบ (44dB)
            </button>
            <button
              className="btn secondary"
              style={{ fontSize: 11, padding: "4px 8px" }}
              onClick={() => simulateNoise(55, 68)}
            >
              ปานกลาง (68dB)
            </button>
            <button
              className="btn secondary"
              style={{ fontSize: 11, padding: "4px 8px" }}
              onClick={() => simulateNoise(72, 86)}
            >
              ดังมาก (86dB)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
