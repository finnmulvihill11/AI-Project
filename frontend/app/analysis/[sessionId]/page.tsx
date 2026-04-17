import Link from "next/link";

// Mock data — replace with Matthew's API response
const mockAnalysis = {
  company: "Google",
  role: "Software Engineer",
  date: "April 4, 2026",
  overallScore: 7.5,
  categories: [
    { name: "Problem Solving", score: 8 },
    { name: "Communication", score: 7 },
    { name: "Technical Knowledge", score: 8 },
  ],
  questions: [
    {
      question: "Design a URL shortener that handles 100M requests per day.",
      score: 8,
      feedback:
        "Strong systems thinking. Good coverage of scalability concerns and hashing strategy. Could improve on database sharding discussion.",
    },
    {
      question: "Given a linked list, remove all consecutive nodes that sum to zero.",
      score: 7,
      feedback:
        "Correct approach with prefix sums. Solution was clean but took longer than ideal to arrive at the optimal time complexity.",
    },
    {
      question: "Tell me about a time you had to make a decision with incomplete information.",
      score: 8,
      feedback:
        "Clear STAR structure. Good use of a concrete example. Could expand on the outcome and what you'd do differently.",
    },
  ],
  strengths: ["Clear problem decomposition", "Strong communication throughout", "Good edge case awareness"],
  improvements: ["Speed up initial approach selection", "Deeper system design depth for senior-level questions"],
};

export default async function AnalysisPage({ params }: PageProps<"/analysis/[sessionId]">) {
  const { sessionId } = await params;
  void sessionId; // will be used to fetch real data from Matthew's API

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      {/* Header */}
      <div className="mb-10">
        <p className="text-sm text-neutral-500 mb-1">
          {mockAnalysis.company} · {mockAnalysis.role} · {mockAnalysis.date}
        </p>
        <h1 className="text-3xl font-bold text-[#0a0a0a]">Interview Analysis</h1>
      </div>

      {/* Overall score */}
      <div className="flex items-center gap-6 p-6 border border-[#e5e5e5] rounded-lg mb-8">
        <div className="text-6xl font-bold text-[#f5c518]">{mockAnalysis.overallScore}</div>
        <div>
          <p className="text-sm text-neutral-500 mb-3">Overall score</p>
          <div className="flex gap-6">
            {mockAnalysis.categories.map((cat) => (
              <div key={cat.name}>
                <p className="text-xs text-neutral-500 mb-1">{cat.name}</p>
                <p className="font-semibold text-[#0a0a0a]">{cat.score}/10</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Strengths & improvements */}
      <div className="grid grid-cols-2 gap-4 mb-10">
        <div className="border border-[#e5e5e5] rounded-lg p-5">
          <h3 className="text-sm font-semibold text-[#0a0a0a] mb-3">Strengths</h3>
          <ul className="space-y-2">
            {mockAnalysis.strengths.map((s) => (
              <li key={s} className="flex items-start gap-2 text-sm text-neutral-500">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#f5c518] shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </div>
        <div className="border border-[#e5e5e5] rounded-lg p-5">
          <h3 className="text-sm font-semibold text-[#0a0a0a] mb-3">To improve</h3>
          <ul className="space-y-2">
            {mockAnalysis.improvements.map((s) => (
              <li key={s} className="flex items-start gap-2 text-sm text-neutral-500">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-neutral-300 shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Question breakdown */}
      <h2 className="text-lg font-semibold text-[#0a0a0a] mb-4">Question breakdown</h2>
      <div className="space-y-4 mb-12">
        {mockAnalysis.questions.map((q, i) => (
          <div key={i} className="border border-[#e5e5e5] rounded-lg p-5">
            <div className="flex items-start justify-between gap-4 mb-3">
              <p className="text-sm font-medium text-[#0a0a0a]">{q.question}</p>
              <span className="text-lg font-bold text-[#f5c518] shrink-0">{q.score}/10</span>
            </div>
            <p className="text-sm text-neutral-500 leading-relaxed">{q.feedback}</p>
          </div>
        ))}
      </div>

      {/* CTAs */}
      <div className="flex items-center gap-4">
        <Link
          href="/prep"
          className="bg-[#f5c518] text-[#0a0a0a] font-semibold px-6 py-3 rounded-md hover:bg-yellow-400 transition-colors text-sm"
        >
          Practice again
        </Link>
        <Link
          href="/performance"
          className="text-sm text-neutral-500 hover:text-[#0a0a0a] transition-colors"
        >
          View my performance →
        </Link>
      </div>
    </div>
  );
}
