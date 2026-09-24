import { useEffect, useState } from "react";
import { api } from "../api";
import ChatWidget from "../components/ChatWidget.jsx";
import Header from "../components/Header.jsx";

function BuildingPhoto({ src, alt }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <div className="building-photo-placeholder">
        <svg viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4 21V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v17M4 21h16M12 21v-6a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v6M7 6h1M7 10h1M7 14h1M15 17h1"
          />
        </svg>
      </div>
    );
  }

  return <img className="building-photo" src={src} alt={alt} onError={() => setFailed(true)} />;
}

export default function GuestKiosk({ session, onEndSession }) {
  const [buildings, setBuildings] = useState([]);
  const [error, setError] = useState("");
  // Hidden until someone actually asks about a building/room/location --
  // not shown by default (see onAnswered below).
  const [showBuildings, setShowBuildings] = useState(false);

  useEffect(() => {
    api.getBuildings().then(setBuildings).catch((err) => setError(err.message));
  }, []);

  function handleAnswered(question) {
    const q = question.toLowerCase();
    if (/ตึก|อาคาร|ห้อง|ที่ไหน|เดินไปยังไง|สถานที่|ทาง/.test(q)) setShowBuildings(true);
  }

  return (
    <div className="kiosk">
      <Header title="ค้นหาอาคาร/สถานที่" session={session} onEndSession={onEndSession} />
      <div className="main">
        {error && <p className="error-text">{error}</p>}
        <div className="grid">
          <ChatWidget
            cardUid={session?.cardUid}
            autoStart
            onAnswered={handleAnswered}
            greeting={`สวัสดีค่ะ${session?.holder?.full_name ? " " + session.holder.full_name : ""} มีอะไรให้ช่วยไหมคะ`}
          />

          {showBuildings && (
            <div className="card">
              <h3 style={{ marginTop: 0 }}>อาคารและห้อง</h3>
              <div className="building-list">
                {buildings.map((b) => (
                  <div key={b.id} className="building-item">
                    <BuildingPhoto src={b.image_url} alt={b.name_th} />
                    <div className="building-info">
                      <strong>
                        {b.code} - {b.name_th}
                      </strong>
                      {b.description && <p style={{ color: "var(--muted)" }}>{b.description}</p>}
                      {b.rooms.length > 0 && (
                        <p style={{ color: "var(--muted)" }}>
                          ห้อง: {b.rooms.map((r) => r.room_number).join(", ")}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
