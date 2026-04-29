import { useRef, useState, useCallback, useEffect } from "react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
const WS_URL = BACKEND_URL.replace(/^http/, "ws");

export type InterviewStatus = "idle" | "connecting" | "active" | "analyzing" | "done" | "error";

export type InterviewState = {
  status: InterviewStatus;
  interviewerSpeaking: boolean;
  questionIndex: number;
  totalQuestions: number;
  questionCategory: string;
  error: string | null;
  isMuted: boolean;
  analysisReady: boolean;
};

export function useInterview() {
  const [state, setState] = useState<InterviewState>({
    status: "idle",
    interviewerSpeaking: false,
    questionIndex: 0,
    totalQuestions: 0,
    questionCategory: "",
    error: null,
    isMuted: false,
    analysisReady: false,
  });

  const wsRef          = useRef<WebSocket | null>(null);
  const streamRef      = useRef<MediaStream | null>(null);
  const recorderRef    = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Uint8Array[]>([]);
  const audioRef       = useRef<HTMLAudioElement | null>(null);
  const pseudoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function sendJson(data: object) {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }

  async function playAudioBuffer() {
    const chunks = [...audioChunksRef.current];
    audioChunksRef.current = [];

    if (chunks.length === 0) {
      sendJson({ type: "audio_done" });
      return;
    }

    const blob = new Blob(chunks.map(c => c.buffer as ArrayBuffer), { type: "audio/mpeg" });
    const url  = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audioRef.current = audio;
    setState(s => ({ ...s, interviewerSpeaking: true }));

    const finish = () => {
      URL.revokeObjectURL(url);
      setState(s => ({ ...s, interviewerSpeaking: false }));
      sendJson({ type: "audio_done" });
    };

    audio.onended = finish;
    audio.onerror = finish;
    try { await audio.play(); } catch { finish(); }
  }

  async function startMic() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      recorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(e.data);
        }
      };
      recorder.start(250);
    } catch {
      setState(s => ({ ...s, status: "error", error: "Microphone access denied. Please allow mic access and try again." }));
    }
  }

  function stopMic() {
    recorderRef.current?.stop();
    recorderRef.current = null;
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
  }

  const connect = useCallback((sessionId: string) => {
    setState(s => ({ ...s, status: "connecting", error: null }));

    const ws = new WebSocket(`${WS_URL}/ws/interview/${sessionId}`);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => {
      setState(s => ({ ...s, status: "active" }));
      startMic();
    };

    ws.onmessage = async (event) => {
      if (event.data instanceof ArrayBuffer) {
        audioChunksRef.current.push(new Uint8Array(event.data));
        return;
      }

      const msg = JSON.parse(event.data as string) as Record<string, unknown>;

      switch (msg.type) {
        case "question_start":
          setState(s => ({
            ...s,
            questionIndex:    (msg.question_index as number) + 1,
            totalQuestions:   msg.total_questions as number,
            questionCategory: (msg.category as string) ?? "",
          }));
          break;
        case "ai_speaking_start":
          audioChunksRef.current = [];
          break;
        case "ai_speaking_end":
          await playAudioBuffer();
          break;
        case "interview_complete":
          setState(s => ({ ...s, status: "analyzing" }));
          stopMic();
          break;
        case "analysis_ready":
          setState(s => ({ ...s, status: "done", analysisReady: true }));
          break;
        case "error":
          setState(s => ({ ...s, status: "error", error: (msg.message as string) ?? "Unknown error" }));
          stopMic();
          break;
      }
    };

    ws.onclose = () => {
      setState(s => (s.status === "active" ? { ...s, status: "done" } : s));
      stopMic();
    };

    ws.onerror = () => {
      setState(s => ({ ...s, status: "error", error: "Connection failed. Is the backend running on port 8000?" }));
      stopMic();
    };
  }, []);

  const endInterview = useCallback(() => {
    sendJson({ type: "end_interview" });
    stopMic();
    setState(s => ({ ...s, status: "analyzing" }));
  }, []);

  const sendPseudocode = useCallback((content: string) => {
    if (pseudoTimerRef.current) clearTimeout(pseudoTimerRef.current);
    pseudoTimerRef.current = setTimeout(() => sendJson({ type: "pseudocode", content }), 500);
  }, []);

  const toggleMute = useCallback(() => {
    const track = streamRef.current?.getAudioTracks()[0];
    if (!track) return;
    track.enabled = !track.enabled;
    setState(s => ({ ...s, isMuted: !s.isMuted }));
  }, []);

  useEffect(() => {
    return () => {
      stopMic();
      audioRef.current?.pause();
      wsRef.current?.close();
      if (pseudoTimerRef.current) clearTimeout(pseudoTimerRef.current);
    };
  }, []);

  return { ...state, connect, endInterview, sendPseudocode, toggleMute };
}
