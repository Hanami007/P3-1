import { useEffect, useRef, useState } from "react";

export function useAudioNoiseAnalyzer({ active = true, onPeakDetected } = {}) {
  const [currentDb, setCurrentDb] = useState(38);
  const [ambientDb, setAmbientDb] = useState(40);
  const [peakDb, setPeakDb] = useState(42);
  const [loudestAt, setLoudestAt] = useState(null);
  const [condition, setCondition] = useState("quiet"); // quiet | moderate | noisy
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState(null);

  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceRef = useRef(null);
  const streamRef = useRef(null);
  const animFrameRef = useRef(null);
  const peakRef = useRef(42);
  const historyRef = useRef([]);
  const simulatedRef = useRef(false);

  // Helper to determine noise condition
  function calculateCondition(ambient, peak) {
    if (peak > 75 || ambient > 68) return "noisy";
    if (peak > 60 || ambient > 50) return "moderate";
    return "quiet";
  }

  function simulateNoise(amb, pk) {
    simulatedRef.current = true;
    const ambVal = Math.round(amb);
    const pkVal = Math.round(Math.max(amb, pk));
    setAmbientDb(ambVal);
    setPeakDb(pkVal);
    setCurrentDb(pkVal);
    setCondition(calculateCondition(ambVal, pkVal));
    setLoudestAt(new Date());
  }

  function resetPeak() {
    peakRef.current = ambientDb || 40;
    setPeakDb(peakRef.current);
    setLoudestAt(null);
  }

  useEffect(() => {
    if (!active || simulatedRef.current) return;

    let isMounted = true;

    async function initAudio() {
      try {
        if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia) {
          throw new Error("Browser does not support getUserMedia");
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
          },
        });

        if (!isMounted) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }

        streamRef.current = stream;
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioCtx();
        audioContextRef.current = ctx;

        const analyser = ctx.createAnalyser();
        analyser.fftSize = 512;
        analyser.smoothingTimeConstant = 0.3;
        analyserRef.current = analyser;

        const source = ctx.createMediaStreamSource(stream);
        source.connect(analyser);
        sourceRef.current = source;

        setIsListening(true);
        setError(null);

        const dataArray = new Float32Array(analyser.fftSize);

        function analyze() {
          if (!analyserRef.current || !isMounted) return;

          analyserRef.current.getFloatTimeDomainData(dataArray);

          // Calculate Root Mean Square (RMS)
          let sumSquares = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sumSquares += dataArray[i] * dataArray[i];
          }
          const rms = Math.sqrt(sumSquares / dataArray.length);

          // Convert RMS to an estimated Sound Pressure Level in dB (30dB - 100dB range)
          // 0.0001 (silence) -> ~30 dB, 1.0 (clipping) -> ~100 dB
          let db = 30;
          if (rms > 0.00001) {
            const dbFs = 20 * Math.log10(rms);
            db = Math.max(30, Math.min(100, Math.round(92 + dbFs)));
          }

          setCurrentDb(db);

          // Rolling ambient noise floor (rolling average of bottom 50% or recent 30 samples)
          historyRef.current.push(db);
          if (historyRef.current.length > 40) historyRef.current.shift();
          const sorted = [...historyRef.current].sort((a, b) => a - b);
          const medianAmbient = sorted[Math.floor(sorted.length * 0.4)] || 40;
          setAmbientDb(medianAmbient);

          // Check if this is the loudest peak so far
          if (db > peakRef.current) {
            peakRef.current = db;
            setPeakDb(db);
            setLoudestAt(new Date());
            onPeakDetected?.(db);
          }

          setCondition(calculateCondition(medianAmbient, peakRef.current));

          animFrameRef.current = requestAnimationFrame(analyze);
        }

        animFrameRef.current = requestAnimationFrame(analyze);
      } catch (err) {
        if (!isMounted) return;
        setIsListening(false);
        setError(err.message || "Cannot access microphone");
        // Fallback default ambient
        setAmbientDb(42);
        setPeakDb(45);
        setCondition("quiet");
      }
    }

    initAudio();

    return () => {
      isMounted = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== "closed") {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, [active, onPeakDetected]);

  return {
    currentDb,
    ambientDb,
    peakDb,
    loudestAt,
    condition,
    isListening,
    error,
    resetPeak,
    simulateNoise,
  };
}

