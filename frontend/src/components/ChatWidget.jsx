import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const SpeechRecognitionCtor =
  typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;
const speechSynthesisSupported = typeof window !== "undefined" && "speechSynthesis" in window;
const VOICE_SUPPORTED = Boolean(SpeechRecognitionCtor) && speechSynthesisSupported;
const MAX_LISTEN_ERRORS = 3;

// Setting utterance.lang alone isn't enough: if the OS default voice is
// English, Chrome/Edge read Thai text with it. Pick a Thai voice explicitly.
// getVoices() is empty until the browser fires "voiceschanged", so cache it.
let thaiVoice = null;

function pickThaiVoice() {
  const thai = window.speechSynthesis.getVoices().filter((v) => v.lang?.toLowerCase().replace("_", "-").startsWith("th"));
  // Prefer Google's (Chrome) or Microsoft's (Edge/Windows) Thai voices.
  thaiVoice = thai.find((v) => /google/i.test(v.name)) || thai.find((v) => /microsoft/i.test(v.name)) || thai[0] || null;
  if (!thaiVoice) console.warn("No Thai speech voice installed -- replies will be read with the default voice");
}

if (speechSynthesisSupported) {
  pickThaiVoice();
  window.speechSynthesis.addEventListener("voiceschanged", pickThaiVoice);
}

function speak(text) {
  return new Promise((resolve) => {
    if (!speechSynthesisSupported || !text) {
      resolve();
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "th-TH";
    if (thaiVoice) utterance.voice = thaiVoice;
    utterance.onend = resolve;
    utterance.onerror = resolve;
    window.speechSynthesis.speak(utterance);
  });
}

export default function ChatWidget({ cardUid, autoStart = false, greeting, noiseData, quickPrompts = [] }) {
  const [messages, setMessages] = useState([
    { role: "bot", text: greeting || "สวัสดีค่ะ สอบถามข้อมูลสาขาวิทยาการคอมพิวเตอร์ อาคาร หรือสถานที่ได้เลยค่ะ" },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [voiceMode, setVoiceMode] = useState(autoStart && VOICE_SUPPORTED);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  const recognitionRef = useRef(null);
  const voiceModeRef = useRef(voiceMode);
  const errorStreakRef = useRef(0);
  voiceModeRef.current = voiceMode;

  useEffect(() => {
    if (greeting) {
      setMessages([{ role: "bot", text: greeting }]);
    }
  }, [greeting]);

  async function respondTo(text) {
    if (!text || busy) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setBusy(true);
    let reply = "";
    try {
      reply = (await api.chat(text, cardUid)).reply;
      setMessages((m) => [...m, { role: "bot", text: reply }]);
      if (voiceModeRef.current) {
        setSpeaking(true);
        await speak(reply);
        setSpeaking(false);
        if (voiceModeRef.current) startListening();
      }
    } catch (err) {
      reply = `ขออภัย เกิดข้อผิดพลาด: ${err.message}`;
      setMessages((m) => [...m, { role: "bot", text: reply }]);
    } finally {
      setBusy(false);
    }
    return reply;
  }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    await respondTo(text);
  }

  function startListening() {
    if (!VOICE_SUPPORTED || recognitionRef.current) return;
    const recognition = new SpeechRecognitionCtor();
    recognition.lang = "th-TH";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setListening(true);

    recognition.onresult = async (event) => {
      const transcript = event.results[0][0].transcript;
      recognitionRef.current = null;
      setListening(false);
      errorStreakRef.current = 0;
      const reply = await respondTo(transcript);
      if (voiceModeRef.current) {
        setSpeaking(true);
        await speak(reply);
        setSpeaking(false);
        if (voiceModeRef.current) startListening();
      }
    };

    recognition.onerror = () => {
      recognitionRef.current = null;
      setListening(false);
      errorStreakRef.current += 1;
      if (voiceModeRef.current && errorStreakRef.current < MAX_LISTEN_ERRORS) {
        setTimeout(() => voiceModeRef.current && startListening(), 800);
      } else if (errorStreakRef.current >= MAX_LISTEN_ERRORS) {
        setVoiceMode(false);
      }
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      setListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }

  function stopListening() {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    setListening(false);
  }

  useEffect(() => {
    if (!autoStart || !VOICE_SUPPORTED) return;
    (async () => {
      setSpeaking(true);
      await speak(greeting || "สวัสดีค่ะ มีอะไรให้ช่วยไหมคะ");
      setSpeaking(false);
      if (voiceModeRef.current) startListening();
    })();
    return () => {
      window.speechSynthesis?.cancel();
      recognitionRef.current?.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function toggleVoiceMode() {
    if (voiceMode) {
      setVoiceMode(false);
      window.speechSynthesis?.cancel();
      stopListening();
    } else {
      errorStreakRef.current = 0;
      setVoiceMode(true);
      startListening();
    }
  }

  return (
    <div className="card chat">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>AI ผู้ช่วยประจำสาขา</h3>
        {VOICE_SUPPORTED && (
          <button className={`btn ${voiceMode ? "" : "secondary"}`} onClick={toggleVoiceMode}>
            {speaking ? "🔊 กำลังพูด" : listening ? "🎙️ กำลังฟัง" : voiceMode ? "🎙️ โหมดเสียง" : "🎙️ เริ่มสนทนาด้วยเสียง"}
          </button>
        )}
      </div>

      <div className="chat-log">
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
        {busy && <div className="chat-bubble bot">กำลังพิมพ์...</div>}
      </div>

      {/* Noise Warning if ambient/peak noise was loud */}
      {noiseData && (noiseData.condition === "noisy" || noiseData.peakDb > 75) && (
        <div className="chat-noise-alert">
          <span>🔊 ตรวจพบเสียงรอบข้างดัง (Peak {noiseData.peakDb} dB) — แนะนำให้ออกเสียงชัดเจนหรือเข้าใกล้ไมค์</span>
        </div>
      )}

      {/* Quick Prompts Bar */}
      {quickPrompts.length > 0 && (
        <div className="quick-prompts-bar">
          <span className="quick-prompts-label">คำถามด่วน:</span>
          {quickPrompts.map((p, idx) => (
            <button
              key={idx}
              className="quick-chip"
              disabled={busy}
              onClick={() => respondTo(p)}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {!VOICE_SUPPORTED && autoStart && (
        <p className="error-text" style={{ fontSize: 13 }}>
          เบราว์เซอร์นี้ไม่รองรับการสนทนาด้วยเสียง กรุณาพิมพ์คำถามแทน
        </p>
      )}

      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="พิมพ์คำถาม เช่น ห้องปฏิบัติการคอมพิวเตอร์อยู่ที่ไหน"
        />
        <button className="btn" onClick={send} disabled={busy}>
          ส่ง
        </button>
      </div>
    </div>
  );
}
