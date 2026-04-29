import Link from "next/link";
import LogoTicker from "./components/LogoTicker";

const steps = [
  { n: "01", title: "Pick a company and role", body: "Choose from Google, Amazon, Jane Street, and more. Select the role you're targeting." },
  { n: "02", title: "Interview live", body: "Speak your answers out loud. A chat box is always available for code and pseudocode." },
  { n: "03", title: "Get your analysis", body: "Receive a full breakdown of your performance — scores, strengths, and areas to improve." },
];

const stats = [
  { value: "2,400+", label: "Questions" },
  { value: "3", label: "Companies" },
  { value: "45 min", label: "Per session" },
  { value: "Free", label: "To start" },
];

const features = [
  { tag: "Companies", title: "Company-specific style", body: "Google, Amazon, and Jane Street each interview differently. We simulate their actual format and expectations." },
  { tag: "Voice", title: "Speak your answers", body: "Talk through your solution out loud, just like a real interview. No typing required." },
  { tag: "Code", title: "Live code panel", body: "A side panel is always open for pseudocode, diagrams, or working code during technical rounds." },
  { tag: "Feedback", title: "Instant analysis", body: "Scored on problem solving, communication, and technical depth — with specific feedback after every session." },
  { tag: "Questions", title: "Real questions", body: "2,400+ questions sourced from actual interview experiences at top companies." },
  { tag: "Roles", title: "Multiple roles", body: "Software Engineer, Data Scientist, PM, Quant, and more — each with their own interview format." },
];

export default function HomePage() {
  return (
    <div className="flex flex-col">

      {/* Hero */}
      <section className="flex flex-col items-center justify-center text-center px-6 py-20 border-b border-[#e5e5e5]">
        <h1 className="text-8xl font-bold tracking-tighter text-[#0a0a0a] mb-5">
          prep
        </h1>
        <p className="text-lg text-neutral-500 max-w-lg mb-8">
          AI-powered mock interviews for the companies that matter. Practice until it feels real.
        </p>
        <Link
          href="/sign-up"
          className="bg-[#f5c518] text-[#0a0a0a] font-semibold px-7 py-2.5 rounded-md hover:bg-yellow-400 transition-colors text-sm"
        >
          Start practicing
        </Link>
      </section>

      {/* Stats */}
      <section className="border-b border-[#e5e5e5]">
        <div className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-4 divide-x divide-[#e5e5e5]">
          {stats.map((s) => (
            <div key={s.label} className="flex flex-col items-center gap-1 px-6">
              <span className="text-3xl font-bold text-[#0a0a0a] tracking-tight">{s.value}</span>
              <span className="text-xs text-neutral-500 uppercase tracking-wider">{s.label}</span>
            </div>
          ))}
        </div>
      </section>

      <LogoTicker />

      {/* Features */}
      <section className="border-b border-[#e5e5e5]">
        <div className="max-w-6xl mx-auto px-6 py-16 w-full">
          <p className="text-xs text-neutral-400 uppercase tracking-widest mb-8">What you get</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {features.map((f) => (
              <div key={f.title} className="border border-[#e5e5e5] rounded-xl p-5">
                <span className="text-xs font-mono text-[#f5c518] mb-2 block">{f.tag}</span>
                <p className="font-semibold text-[#0a0a0a] text-sm mb-1">{f.title}</p>
                <p className="text-xs text-neutral-500 leading-relaxed">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-6xl mx-auto px-6 py-16 w-full">
        <p className="text-xs text-neutral-400 uppercase tracking-widest mb-8">How it works</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
          {steps.map((s) => (
            <div key={s.n}>
              <span className="text-xs font-mono text-[#f5c518] mb-3 block">{s.n}</span>
              <h3 className="font-semibold text-[#0a0a0a] mb-2">{s.title}</h3>
              <p className="text-sm text-neutral-500 leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA strip */}
      <section className="border-t border-[#e5e5e5] bg-[#f5f5f5]">
        <div className="max-w-6xl mx-auto px-6 py-14 flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <p className="font-semibold text-[#0a0a0a]">One free interview, no credit card required.</p>
            <p className="text-sm text-neutral-500 mt-1">Create an account and start your first mock interview today.</p>
          </div>
          <Link
            href="/sign-up"
            className="bg-[#0a0a0a] text-white font-semibold px-6 py-2.5 rounded-md hover:bg-neutral-800 transition-colors text-sm whitespace-nowrap"
          >
            Get started free
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#e5e5e5]">
        <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
          <span className="text-sm font-bold tracking-tight text-[#0a0a0a]">prep</span>
          <span className="text-xs text-neutral-400">© 2026 prep</span>
        </div>
      </footer>

    </div>
  );
}
