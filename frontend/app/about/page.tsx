const companies = [
  {
    name: "Google",
    description: "Coding, system design, and behavioral questions sourced from real interview experiences. Covers Software Engineer, Data Scientist, and more.",
    types: ["Coding", "System Design", "Behavioral"],
  },
  {
    name: "Amazon",
    description: "LeetCode-style problems paired with Leadership Principles behavioral questions — the format Amazon is known for.",
    types: ["Coding", "Behavioral", "Leadership Principles"],
  },
  {
    name: "Jane Street",
    description: "Quantitative reasoning, functional programming, and probability questions. Curated from blogs, Reddit, and GitHub.",
    types: ["Quantitative", "Functional Programming", "Probability"],
  },
];

const team = [
  {
    name: "Finn Mulvihill",
    role: "Data & Infrastructure",
    bio: "Builds the scraper pipeline, question database, and data infrastructure that powers the platform.",
  },
  {
    name: "Matthew",
    role: "AI & Interview Engine",
    bio: "Builds the AI model, voice interview orchestration, and post-interview scoring and analysis.",
  },
];

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-20">

      {/* Header */}
      <div className="mb-16">
        <h1 className="text-3xl font-bold text-[#0a0a0a] mb-4">About</h1>
        <p className="text-neutral-500 leading-relaxed">
          prep is an AI-powered mock interview platform built to simulate real technical interviews at the companies that matter most. Practice out loud, get honest feedback, and improve with every session.
        </p>
      </div>

      {/* How it works */}
      <section id="how-it-works" className="mb-16 scroll-mt-20">
        <p className="text-xs text-neutral-400 uppercase tracking-widest mb-6">How it works</p>
        <div className="space-y-6">
          {[
            { n: "01", title: "Choose your target", body: "Select a company and role. prep matches you with questions drawn from real interview experiences at that company." },
            { n: "02", title: "Interview live with AI", body: "The AI interviewer speaks and listens in real time — just like a real interview. A code box is available for pseudocode, algorithms, or anything that needs to be written." },
            { n: "03", title: "Get your analysis", body: "After every session, receive a detailed breakdown — overall score, category scores, per-question feedback, and specific areas to improve." },
          ].map((s) => (
            <div key={s.n} className="flex gap-5">
              <span className="text-xs font-mono text-[#f5c518] mt-0.5 shrink-0">{s.n}</span>
              <div>
                <h3 className="font-semibold text-[#0a0a0a] mb-1">{s.title}</h3>
                <p className="text-sm text-neutral-500 leading-relaxed">{s.body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Companies */}
      <section id="companies" className="mb-16 scroll-mt-20">
        <p className="text-xs text-neutral-400 uppercase tracking-widest mb-6">Supported companies</p>
        <div className="space-y-4">
          {companies.map((c) => (
            <div key={c.name} className="border border-[#e5e5e5] rounded-lg p-5">
              <div className="flex items-start justify-between gap-4 mb-2">
                <h3 className="font-semibold text-[#0a0a0a]">{c.name}</h3>
                <div className="flex flex-wrap gap-1.5 justify-end">
                  {c.types.map((t) => (
                    <span key={t} className="text-xs bg-[#f5f5f5] text-neutral-500 px-2 py-0.5 rounded">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
              <p className="text-sm text-neutral-500 leading-relaxed">{c.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Team */}
      <section id="team" className="mb-16 scroll-mt-20">
        <p className="text-xs text-neutral-400 uppercase tracking-widest mb-6">Team</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {team.map((t) => (
            <div key={t.name} className="border border-[#e5e5e5] rounded-lg p-5">
              <p className="font-semibold text-[#0a0a0a] mb-0.5">{t.name}</p>
              <p className="text-xs text-[#f5c518] font-medium mb-3">{t.role}</p>
              <p className="text-sm text-neutral-500 leading-relaxed">{t.bio}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="scroll-mt-20">
        <p className="text-xs text-neutral-400 uppercase tracking-widest mb-6">Pricing</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-[#e5e5e5] rounded-lg p-5">
            <p className="font-semibold text-[#0a0a0a] mb-0.5">Free</p>
            <p className="text-xs text-neutral-400 mb-4">No credit card required</p>
            <ul className="space-y-2 text-sm text-neutral-500">
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[#f5c518] shrink-0" />1 full mock interview</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[#f5c518] shrink-0" />Full post-interview analysis</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[#f5c518] shrink-0" />All supported companies</li>
            </ul>
          </div>
          <div className="border border-[#0a0a0a] rounded-lg p-5">
            <p className="font-semibold text-[#0a0a0a] mb-0.5">Pro</p>
            <p className="text-xs text-neutral-400 mb-4">Coming soon</p>
            <ul className="space-y-2 text-sm text-neutral-500">
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[#0a0a0a] shrink-0" />Unlimited interviews</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[#0a0a0a] shrink-0" />Performance tracking over time</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[#0a0a0a] shrink-0" />Priority access to new companies</li>
            </ul>
          </div>
        </div>
      </section>

    </div>
  );
}
