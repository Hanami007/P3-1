import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, DAY_NAMES_TH } from "../api";
import ChatWidget from "../components/ChatWidget.jsx";
import Header from "../components/Header.jsx";

export default function StudentDashboard({ session, onEndSession }) {
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState([]);
  const [exams, setExams] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session) {
      navigate("/");
      return;
    }
    (async () => {
      try {
        const [scheduleData, examData, announcementData] = await Promise.all([
          api.getSchedule(session.cardUid),
          api.getExams(session.cardUid),
          api.getAnnouncements(session.cardUid),
        ]);
        setSchedule(scheduleData);
        setExams(examData);
        setAnnouncements(announcementData);
      } catch (err) {
        setError(err.message);
      }
    })();
  }, [session, navigate]);

  if (!session) return null;

  return (
    <div className="kiosk">
      <Header title="ตารางเรียน/ตารางสอบ" session={session} onEndSession={onEndSession} />
      <div className="main">
        {error && <p className="error-text">{error}</p>}

        <div className="grid">
          <div className="card">
            <h3 style={{ marginTop: 0 }}>ตารางเรียนประจำสัปดาห์</h3>
            <table>
              <thead>
                <tr>
                  <th>วัน</th>
                  <th>เวลา</th>
                  <th>วิชา</th>
                  <th>ห้อง</th>
                </tr>
              </thead>
              <tbody>
                {schedule.map((s) => (
                  <tr key={s.id}>
                    <td>{DAY_NAMES_TH[s.day_of_week]}</td>
                    <td>{s.start_time} - {s.end_time}</td>
                    <td>{s.course.code} {s.course.name_th}</td>
                    <td>{s.room ? `${s.room.room_number} (ชั้น ${s.room.floor})` : "-"}</td>
                  </tr>
                ))}
                {schedule.length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ color: "var(--muted)" }}>
                      ไม่มีตารางเรียน
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3 style={{ marginTop: 0 }}>ตารางสอบ</h3>
            <table>
              <thead>
                <tr>
                  <th>วันที่</th>
                  <th>เวลา</th>
                  <th>วิชา</th>
                  <th>ห้อง</th>
                  <th>ประเภท</th>
                </tr>
              </thead>
              <tbody>
                {exams.map((e) => (
                  <tr key={e.id}>
                    <td>{e.exam_date}</td>
                    <td>{e.start_time} - {e.end_time}</td>
                    <td>{e.course.code} {e.course.name_th}</td>
                    <td>{e.room ? e.room.room_number : "-"}</td>
                    <td>{e.exam_type === "final" ? "ปลายภาค" : "กลางภาค"}</td>
                  </tr>
                ))}
                {exams.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ color: "var(--muted)" }}>
                      ไม่มีตารางสอบ
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3 style={{ marginTop: 0 }}>ข่าวสารสาขา</h3>
            {announcements.map((a) => (
              <div key={a.id} style={{ marginBottom: 12 }}>
                <strong>{a.title}</strong>
                <p style={{ color: "var(--muted)" }}>{a.body}</p>
              </div>
            ))}
            {announcements.length === 0 && <p style={{ color: "var(--muted)" }}>ไม่มีประกาศ</p>}
          </div>

          <ChatWidget
            cardUid={session.cardUid}
            autoStart
            greeting={`สวัสดีค่ะ ${session.holder?.full_name ?? ""} มีอะไรให้ช่วยไหมคะ`}
          />
        </div>
      </div>
    </div>
  );
}
