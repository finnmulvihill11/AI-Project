"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const companies = [
  {
    id: "google",
    name: "Google",
    roles: ["Software Engineer", "Data Scientist", "Product Manager", "Site Reliability Engineer"],
  },
  {
    id: "amazon",
    name: "Amazon",
    roles: ["Software Engineer", "Data Scientist", "Product Manager", "Solutions Architect"],
  },
  {
    id: "jane-street",
    name: "Jane Street",
    roles: ["Software Engineer", "Quantitative Trader", "Quantitative Researcher"],
  },
];

export default function PrepPage() {
  const router = useRouter();
  const [selected, setSelected] = useState<{ company: string; role: string } | null>(null);

  function handleStart() {
    if (!selected) return;
    // TODO: create session via API, redirect to /interview/[sessionId]
    router.push("/interview/demo-session");
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-16">
      <div className="mb-12">
        <h1 className="text-3xl font-bold text-[#0a0a0a] mb-2">Choose your interview</h1>
        <p className="text-neutral-500 text-sm">
          Select a company and role to begin your mock interview.
        </p>
      </div>

      {/* Free trial badge */}
      <div className="inline-flex items-center gap-2 bg-[#f5c518]/20 border border-[#f5c518] text-[#0a0a0a] text-xs font-medium px-3 py-1.5 rounded-full mb-10">
        <span className="w-1.5 h-1.5 rounded-full bg-[#f5c518]" />
        You have 1 free interview remaining
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
        {companies.map((company) => (
          <div
            key={company.id}
            className={`border rounded-lg p-5 cursor-pointer transition-all ${
              selected?.company === company.id
                ? "border-[#0a0a0a] bg-[#f5f5f5]"
                : "border-[#e5e5e5] hover:border-neutral-300"
            }`}
            onClick={() =>
              setSelected((prev) =>
                prev?.company === company.id
                  ? null
                  : { company: company.id, role: company.roles[0] }
              )
            }
          >
            <div className="flex items-center justify-between mb-4">
              <span className="font-semibold text-[#0a0a0a]">{company.name}</span>
              {selected?.company === company.id && (
                <span className="w-2 h-2 rounded-full bg-[#f5c518]" />
              )}
            </div>

            <select
              className="w-full text-sm text-neutral-500 bg-white border border-[#e5e5e5] rounded px-2 py-1.5 focus:outline-none focus:border-[#0a0a0a]"
              value={selected?.company === company.id ? selected.role : company.roles[0]}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) =>
                setSelected({ company: company.id, role: e.target.value })
              }
            >
              {company.roles.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      <button
        onClick={handleStart}
        disabled={!selected}
        className={`px-8 py-3 rounded-md font-semibold text-sm transition-colors ${
          selected
            ? "bg-[#f5c518] text-[#0a0a0a] hover:bg-yellow-400 cursor-pointer"
            : "bg-[#e5e5e5] text-neutral-500 cursor-not-allowed"
        }`}
      >
        Start interview
      </button>
    </div>
  );
}
