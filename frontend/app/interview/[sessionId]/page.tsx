"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useInterview } from "../../../lib/useInterview";

type SessionContext = { company: string; role: string };

function getSessionContext(): SessionContext {
  if (typeof window === "undefined") return { company: "", role: "" };
  try {
    const raw = localStorage.getItem("pendingSession");
    return raw ? (JSON.parse(raw) as SessionContext) : { company: "", role: "" };
  } catch {
    return { company: "", role: "" };
  }
}

export default function InterviewPage() {
  const router    = useRouter();
  const params    = useParams();
  const sessionId = params.sessionId as string;

  const interview = useInterview();
  const [elapsed, setElapsed]     = useState(0);
  const [codeInput, setCodeInput] = useState("");
  const [session, setSession]     = useState<SessionContext>({ company: "", role: "" });

  useEffect(() => { setSession(getSessionContext()); }, []);

  useEffect(() => {
    if (sessionId) interview.connect(sessionId);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    if (interview.analysisReady) router.push(`/analysis/${sessionId}`);
  }, [interview.analysisReady, sessionId, router]);

  useEffect(() => {
    if (interview.status !== "active") return;
    const id = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(id);
  }, [interview.status]);

  const { sendPseudocode } = interview;
  useEffect(() => {
    if (codeInput) sendPseudocode(codeInput);
  }, [codeInput, sendPseudocode]);

  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  // ── Connecting ──────────────────────────────────────────────────────────────

  if (interview.status === "idle" || interview.status === "connecting") {
    return (
      <div className="h-screen bg-[#1c1c1e] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 rounded-full border-2 border-white/20 border-t-white/60 animate-spin" />
          <p className="text-sm text-white/30">Connecting...</p>
        </div>
      </div>
    );
  }

  // ── Error ───────────────────────────────────────────────────────────────────

  if (interview.status === "error") {
    return (
      <div className="h-screen bg-[#1c1c1e] flex items-center justify-center px-6">
        <div className="flex flex-col items-center gap-4 text-center max-w-sm">
          <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center">
            <span className="text-red-400 font-bold">!</span>
          </div>
          <p className="text-sm font-semibold text-white/60">Something went wrong</p>
          <p className="text-xs text-white/25">{interview.error}</p>
          <button
            onClick={() => router.push("/prep")}
            className="text-sm text-white/40 hover:text-white/70 underline transition-colors"
          >
            Back to prep
          </button>
        </div>
      </div>
    );
  }

  // ── Active / Analyzing ──────────────────────────────────────────────────────

  const isAnalyzing = interview.status === "analyzing" || interview.status === "done";

  return (
    <div className="h-screen bg-[#1c1c1e] text-white flex flex-col">

      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold">{session.company || "Interview"}</span>
          {session.role && (
            <>
              <span className="text-white/20">·</span>
              <span className="text-sm text-white/50">{session.role}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-3">
          {isAnalyzing ? (
            <span className="text-xs text-white/25">Generating analysis...</span>
          ) : (
            <>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                <span className="text-xs text-white/30">Live</span>
              </div>
              <span className="text-sm font-mono text-white/40 tabular-nums">{mm}:{ss}</span>
            </>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left — voice panel */}
        <div className="flex-1 flex flex-col items-center justify-center border-r border-white/10 px-8 gap-8">

          {/* Speaking indicator */}
          <div className="flex flex-col items-center gap-5">
            <div className="relative flex items-center justify-center w-36 h-36">
              {interview.interviewerSpeaking && (
                <div className="absolute inset-0 rounded-full bg-[#f5c518]/5 animate-ping" />
              )}
              <div
                className={`absolute inset-4 rounded-full transition-all duration-700 ${
                  interview.interviewerSpeaking ? "bg-[#f5c518]/10" : "bg-white/5"
                }`}
              />
              <div
                className={`absolute inset-8 rounded-full transition-all duration-500 ${
                  interview.interviewerSpeaking ? "bg-[#f5c518]/20" : "bg-white/[0.06]"
                }`}
              />
              <div
                className={`w-5 h-5 rounded-full transition-all duration-300 ${
                  isAnalyzing
                    ? "bg-white/10"
                    : interview.interviewerSpeaking
                    ? "bg-[#f5c518] scale-110"
                    : "bg-white/25"
                }`}
              />
            </div>

            <div className="flex flex-col items-center gap-1 text-center">
              <p className="text-xs font-semibold uppercase tracking-widest text-white/50">
                {isAnalyzing
                  ? "Scoring"
                  : interview.interviewerSpeaking
                  ? "Interviewer"
                  : "You"}
              </p>
              <p className="text-sm text-white/25">
                {isAnalyzing
                  ? "Generating your analysis..."
                  : interview.interviewerSpeaking
                  ? "Speaking..."
                  : "Your turn to respond"}
              </p>
            </div>
          </div>

          {/* Question progress */}
          {interview.totalQuestions > 0 && !isAnalyzing && (
            <div className="flex items-center gap-2">
              {Array.from({ length: interview.totalQuestions }).map((_, i) => (
                <div
                  key={i}
                  className={`h-1 w-8 rounded-full transition-all duration-300 ${
                    i < interview.questionIndex - 1
                      ? "bg-[#f5c518]"
                      : i === interview.questionIndex - 1
                      ? "bg-[#f5c518]/50"
                      : "bg-white/10"
                  }`}
                />
              ))}
              <span className="text-xs text-white/20 ml-1 font-mono">
                {interview.questionIndex}/{interview.totalQuestions}
              </span>
            </div>
          )}
        </div>

        {/* Right — code panel */}
        <div className="w-96 flex flex-col">
          <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
            <p className="text-xs text-white/40 uppercase tracking-wider">Code / Notes</p>
            <span className="text-[10px] text-white/20 font-mono bg-white/5 px-2 py-0.5 rounded">
              plaintext
            </span>
          </div>
          <textarea
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value)}
            placeholder="Write pseudocode, notes, or code here..."
            disabled={isAnalyzing}
            className="flex-1 bg-transparent text-sm text-white/70 font-mono p-4 resize-none focus:outline-none placeholder:text-white/15 leading-relaxed disabled:opacity-40"
          />
        </div>
      </div>

      {/* Bottom bar */}
      <div className="flex items-center justify-between px-6 py-4 border-t border-white/10">
        <button
          onClick={interview.toggleMute}
          disabled={isAnalyzing}
          className={`text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${
            interview.isMuted
              ? "bg-white/10 text-white/35"
              : "bg-white/5 text-white/55 hover:bg-white/10"
          }`}
        >
          {interview.isMuted ? "Unmute" : "Mute"}
        </button>

        <button
          onClick={interview.endInterview}
          disabled={isAnalyzing}
          className="text-sm bg-red-500/10 text-red-400/80 px-5 py-2 rounded-lg hover:bg-red-500/20 transition-colors border border-red-500/20 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          End interview
        </button>
      </div>

    </div>
  );
}
