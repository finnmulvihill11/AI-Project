"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";

// Mock interview state — replace with Matthew's API
const MOCK_COMPANY = "Google";
const MOCK_ROLE = "Software Engineer";

type Message = {
  role: "interviewer" | "you";
  text: string;
};

const INITIAL_MESSAGES: Message[] = [
  {
    role: "interviewer",
    text: `Hi, I'm your interviewer today. We're doing a ${MOCK_ROLE} interview at ${MOCK_COMPANY}. Let's start with a coding problem. Are you ready?`,
  },
];

export default function InterviewPage() {
  const router = useRouter();
  const [muted, setMuted] = useState(false);
  const [speaking, setSpeaking] = useState(true); // interviewer speaking state
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [codeInput, setCodeInput] = useState("");
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Simulate interviewer finishing speaking after 2s
    const t = setTimeout(() => setSpeaking(false), 2000);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function handleEndInterview() {
    router.push("/analysis/demo-session");
  }

  return (
    <div className="h-screen bg-[#0a0a0a] text-white flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold">{MOCK_COMPANY}</span>
          <span className="text-white/30">·</span>
          <span className="text-sm text-white/60">{MOCK_ROLE}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-white/40">
          <span>00:00</span>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left — voice panel */}
        <div className="flex-1 flex flex-col items-center justify-center border-r border-white/10 px-8">
          {/* Speaking indicator */}
          <div className="flex flex-col items-center gap-6 mb-12">
            <div className="relative flex items-center justify-center">
              <div
                className={`w-20 h-20 rounded-full bg-[#f5c518]/10 flex items-center justify-center transition-all ${
                  speaking ? "scale-110" : "scale-100"
                }`}
              >
                <div
                  className={`w-4 h-4 rounded-full bg-[#f5c518] transition-all ${
                    speaking ? "animate-pulse scale-125" : ""
                  }`}
                />
              </div>
              {speaking && (
                <div className="absolute inset-0 rounded-full bg-[#f5c518]/20 animate-ping" />
              )}
            </div>
            <p className="text-sm text-white/40">
              {speaking ? "Interviewer is speaking..." : "Your turn"}
            </p>
          </div>

          {/* Message feed */}
          <div
            ref={chatRef}
            className="w-full max-w-md h-48 overflow-y-auto space-y-3 scrollbar-none"
          >
            {messages.map((msg, i) => (
              <div key={i} className={`text-sm ${msg.role === "interviewer" ? "text-white/80" : "text-white/50 text-right"}`}>
                <span className="text-xs uppercase tracking-wider text-white/30 mr-2">
                  {msg.role === "interviewer" ? "Interviewer" : "You"}
                </span>
                {msg.text}
              </div>
            ))}
          </div>
        </div>

        {/* Right — code/text panel */}
        <div className="w-96 flex flex-col">
          <div className="px-4 py-3 border-b border-white/10">
            <p className="text-xs text-white/40 uppercase tracking-wider">Code / Notes</p>
          </div>
          <textarea
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value)}
            placeholder="Write pseudocode, notes, or code here..."
            className="flex-1 bg-transparent text-sm text-white/80 font-mono p-4 resize-none focus:outline-none placeholder:text-white/20"
          />
        </div>
      </div>

      {/* Bottom bar */}
      <div className="flex items-center justify-between px-6 py-4 border-t border-white/10">
        <button
          onClick={() => setMuted((m) => !m)}
          className={`flex items-center gap-2 text-sm px-4 py-2 rounded-md transition-colors ${
            muted
              ? "bg-white/10 text-white/40"
              : "bg-white/5 text-white/70 hover:bg-white/10"
          }`}
        >
          {muted ? "Unmute" : "Mute"}
        </button>

        <button
          onClick={handleEndInterview}
          className="text-sm bg-red-500/20 text-red-400 px-4 py-2 rounded-md hover:bg-red-500/30 transition-colors"
        >
          End interview
        </button>
      </div>
    </div>
  );
}
