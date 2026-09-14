import { useEffect, useState } from "react";
import { api } from "../api";
import ChatWidget from "../components/ChatWidget.jsx";
import Header from "../components/Header.jsx";

export default function GuestKiosk({ session, onEndSession }) {
  const [buildings, setBuildings] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getBuildings().then(setBuildings).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="kiosk">
      <Header title="ค้นหาอาคาร/สถานที่" session={session} onEndSession={onEndSession} />
      <div className="main">
        {error && <p className="error-text">{error}</p>}
        <div className="grid">
          <div className="card">
            <h3 style={{ marginTop: 0 }}>อาคารและห้อง</h3>
            {buildings.map((b) => (
              <div key={b.id} style={{ marginBottom: 16 }}>
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
            ))}
          </div>

          <ChatWidget
            cardUid={session?.cardUid}
            autoStart
            greeting={`สวัสดีค่ะ${session?.holder?.full_name ? " " + session.holder.full_name : ""} มีอะไรให้ช่วยไหมคะ`}
          />
        </div>
      </div>
    </div>
  );
}
