import Link from "next/link";

// Mock data — replace with real DB queries
const mockHistory = [
  { id: "1", company: "Google", role: "Software Engineer", date: "Apr 4, 2026", score: 7.5 },
  { id: "2", company: "Amazon", role: "Software Engineer", date: "Mar 28, 2026", score: 6.0 },
  { id: "3", company: "Google", role: "Software Engineer", date: "Mar 20, 2026", score: 6.5 },
];

const avgScore = (
  mockHistory.reduce((sum, h) => sum + h.score, 0) / mockHistory.length
).toFixed(1);

export default function PerformancePage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-16">
      <div className="mb-12">
        <h1 className="text-3xl font-bold text-[#0a0a0a] mb-2">My Performance</h1>
        <p className="text-sm text-neutral-500">Track your progress across all mock interviews.</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-12">
        <div className="border border-[#e5e5e5] rounded-lg p-5">
          <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Interviews</p>
          <p className="text-3xl font-bold text-[#0a0a0a]">{mockHistory.length}</p>
        </div>
        <div className="border border-[#e5e5e5] rounded-lg p-5">
          <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Avg. score</p>
          <p className="text-3xl font-bold text-[#f5c518]">{avgScore}</p>
        </div>
        <div className="border border-[#e5e5e5] rounded-lg p-5">
          <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Best score</p>
          <p className="text-3xl font-bold text-[#0a0a0a]">
            {Math.max(...mockHistory.map((h) => h.score)).toFixed(1)}
          </p>
        </div>
      </div>

      {/* Score trend placeholder */}
      <div className="border border-[#e5e5e5] rounded-lg p-6 mb-10">
        <p className="text-sm font-semibold text-[#0a0a0a] mb-4">Score over time</p>
        <div className="flex items-end gap-3 h-24">
          {mockHistory
            .slice()
            .reverse()
            .map((h, i) => (
              <div key={i} className="flex flex-col items-center gap-1">
                <div
                  className="w-10 bg-[#f5c518] rounded-sm"
                  style={{ height: `${(h.score / 10) * 96}px` }}
                />
                <span className="text-xs text-neutral-500">{h.score}</span>
              </div>
            ))}
        </div>
      </div>

      {/* Interview history */}
      <h2 className="text-lg font-semibold text-[#0a0a0a] mb-4">Interview history</h2>
      <div className="border border-[#e5e5e5] rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#f5f5f5] border-b border-[#e5e5e5]">
            <tr>
              <th className="text-left px-5 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wider">Company</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wider">Role</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wider">Date</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-neutral-500 uppercase tracking-wider">Score</th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-[#e5e5e5]">
            {mockHistory.map((h) => (
              <tr key={h.id} className="hover:bg-[#f5f5f5]/50 transition-colors">
                <td className="px-5 py-4 font-medium text-[#0a0a0a]">{h.company}</td>
                <td className="px-5 py-4 text-neutral-500">{h.role}</td>
                <td className="px-5 py-4 text-neutral-500">{h.date}</td>
                <td className="px-5 py-4 font-semibold text-[#f5c518]">{h.score}/10</td>
                <td className="px-5 py-4 text-right">
                  <Link
                    href={`/analysis/${h.id}`}
                    className="text-xs text-neutral-500 hover:text-[#0a0a0a] transition-colors"
                  >
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
