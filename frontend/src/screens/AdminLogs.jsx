import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Header from "../components/Header.jsx";

export default function AdminLogs({ session, onEndSession }) {
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session) {
      navigate("/");
      return;
    }
    api.getLogs(session.cardUid).then(setLogs).catch((err) => setError(err.message));
  }, [session, navigate]);

  if (!session) return null;

  return (
    <div className="kiosk">
      <Header title="ประวัติการใช้งาน (Log)" session={session} onEndSession={onEndSession} />
      <div className="main">
        {error && <p className="error-text">{error}</p>}
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>เวลา</th>
                <th>บัตร</th>
                <th>สิทธิ์</th>
                <th>การกระทำ</th>
                <th>รายละเอียด</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td>{new Date(l.timestamp).toLocaleString("th-TH")}</td>
                  <td>{l.card_uid ?? "-"}</td>
                  <td>{l.role ?? "-"}</td>
                  <td>{l.action}</td>
                  <td>{l.detail ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
