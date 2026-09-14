import { useEffect, useState } from "react";

function useClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export default function Header({ title, session, onEndSession }) {
  const now = useClock();
  return (
    <div className="topbar">
      <h1>{title}</h1>
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        {session?.holder && (
          <span className="badge">
            {session.holder.full_name} · {session.role}
          </span>
        )}
        <span className="clock">{now.toLocaleTimeString("th-TH")}</span>
        {session && (
          <button className="btn danger" onClick={onEndSession}>
            จบการใช้งาน
          </button>
        )}
      </div>
    </div>
  );
}
