import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, DAY_NAMES_TH } from "../api";
import ChatWidget from "../components/ChatWidget.jsx";
import Header from "../components/Header.jsx";

export default function StudentDashboard({ session, onEndSession }) {
  const navigate = useNavigate();
  const [liveStatus, setLiveStatus] = useState(session?.liveStatus || null);
  const [schedule, setSchedule] = useState([]);
  const [exams, setExams] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [showFullSchedule, setShowFullSchedule] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session) {
      navigate("/");
      return;
    }

    (async () => {
      try {
        // If liveStatus wasn't pre-populated, load it
        if (!session.liveStatus) {
          const status = await api.getLiveStatus(session.cardUid);
          setLiveStatus(status);
        }

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

  const currentGreeting =
    session.smartGreeting ||
    liveStatus?.smart_greeting ||
    `สวัสดีครับคุณ ${session.holder?.full_name ?? ""} มีอะไรให้สอบถามไหมครับ`;

  return (
    <div className="kiosk">
      <Header title="ผู้ช่วยอัจฉริยะนักศึกษา" session={session} onEndSession={onEndSession} />
      <div className="main">
        {error && <p className="error-text">{error}</p>}

        {/* Real-time Status Alert Banner */}
        {liveStatus && (
          <div className={`live-status-banner ${liveStatus.status}`}>
            <div className="banner-icon">
              {liveStatus.status === "ongoing_late" && "🚨"}
              {liveStatus.status === "ongoing_in_class" && "📚"}
              {liveStatus.status === "upcoming_soon" && "⏳"}
              {liveStatus.status === "upcoming_later" && "📖"}
              {liveStatus.status === "exam_today" && "🎯"}
              {liveStatus.status === "finished_today" && "✅"}
              {liveStatus.status === "no_classes_today" && "☕"}
            </div>
            <div className="banner-content">
              <div className="banner-title">
                {liveStatus.status === "ongoing_late" && "ตอนนี้เลยเวลาเริ่มเรียนแล้ว (สายแล้วนะ!)"}
                {liveStatus.status === "ongoing_in_class" && "กำลังอยู่ในเวลาเรียน (อาจารย์กำลังสอน)"}
                {liveStatus.status === "upcoming_soon" && "เตรียมตัวเข้าเรียน (อีกสักครู่จะเริ่มสอน)"}
                {liveStatus.status === "upcoming_later" && "วิชาเรียนถัดไปสำหรับวันนี้"}
                {liveStatus.status === "exam_today" && "วันนี้คุณมีตารางสอบ"}
                {liveStatus.status === "finished_today" && "เรียนครบทุกวิชาแล้วสำหรับวันนี้"}
                {liveStatus.status === "no_classes_today" && "วันนี้ไม่มีตารางเรียน"}
              </div>
              <div className="banner-desc">{liveStatus.smart_greeting}</div>
            </div>
            {liveStatus.current_time && (
              <div className="banner-time">
                <span>เวลาขณะนี้</span>
                <strong>{liveStatus.current_time} น.</strong>
              </div>
            )}
          </div>
        )}

        {/* Primary Feature: AI Conversational Voice/Chat Assistant */}
        <div className="conversational-container">
          <ChatWidget
            cardUid={session.cardUid}
            autoStart={true}
            greeting={currentGreeting}
            noiseData={session.noiseData}
            quickPrompts={[
              "📅 วันนี้มีเรียนวิชาอะไรบ้าง",
              "📍 ห้องเรียนอยู่ที่ไหน เดินไปยังไง",
              "📝 มีตารางสอบวันไหนบ้าง",
              "🔔 สรุปประกาศข่าวสารของสาขา",
              "⏰ คาบถัดไปเริ่มกี่โมง",
            ]}
          />
        </div>

        {/* Collapsible Full Tables View (Accessible on demand) */}
        <div className="full-schedule-drawer">
          <button
            className="btn secondary drawer-toggle-btn"
            onClick={() => setShowFullSchedule(!showFullSchedule)}
          >
            {showFullSchedule
              ? "▲ ซ่อนตารางเรียนและข้อมูลเต็ม"
              : "▼ ดูตารางเรียนประจำสัปดาห์ / ตารางสอบ / ข่าวสารทั้งหมด (ข้อมูลตาราง)"}
          </button>

          {showFullSchedule && (
            <div className="grid full-schedule-grid" style={{ marginTop: 16 }}>
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
