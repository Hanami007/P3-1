import { useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import AdminLogs from "./screens/AdminLogs.jsx";
import GuestKiosk from "./screens/GuestKiosk.jsx";
import ScanScreen from "./screens/ScanScreen.jsx";
import StudentDashboard from "./screens/StudentDashboard.jsx";

export default function App() {
  const [session, setSession] = useState(null);
  const navigate = useNavigate();

  function endSession() {
    setSession(null);
    navigate("/");
  }

  return (
    <Routes>
      <Route path="/" element={<ScanScreen onSession={setSession} />} />
      <Route path="/student" element={<StudentDashboard session={session} onEndSession={endSession} />} />
      <Route path="/staff" element={<AdminLogs session={session} onEndSession={endSession} />} />
      <Route path="/guest" element={<GuestKiosk session={session} onEndSession={endSession} />} />
    </Routes>
  );
}
