"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const interviewFormats = ["Coding", "System Design", "Behavioral", "Case Study", "Technical Screen", "Take-home"];

const knownCompanies: Record<string, string> = {
  google: "Google", meta: "Meta", apple: "Apple", netflix: "Netflix",
  amazon: "Amazon", "jane-street": "Jane Street", stripe: "Stripe",
  coinbase: "Coinbase", palantir: "Palantir", airbnb: "Airbnb",
  uber: "Uber", spotify: "Spotify",
};

function CustomRoleForm() {
  const router = useRouter();
  const params = useSearchParams();
  const source = params.get("source");
  const companyParam = params.get("company");

  const [companyName, setCompanyName] = useState("");
  const [form, setForm] = useState({
    title: "",
    responsibilities: "",
    skills: "",
    formats: [] as string[],
  });

  useEffect(() => {
    if (source === "custom") {
      const stored = localStorage.getItem("customCompany");
      if (stored) setCompanyName(JSON.parse(stored).name);
    } else if (companyParam && knownCompanies[companyParam]) {
      setCompanyName(knownCompanies[companyParam]);
    }
  }, [source, companyParam]);

  const isValid = form.title.trim() && form.responsibilities.trim() && form.formats.length > 0;

  function toggleFormat(f: string) {
    setForm((prev) => ({
      ...prev,
      formats: prev.formats.includes(f) ? prev.formats.filter((x) => x !== f) : [...prev.formats, f],
    }));
  }

  function handleStart() {
    if (!isValid) return;
    const customCompany = source === "custom" ? JSON.parse(localStorage.getItem("customCompany") ?? "{}") : null;
    localStorage.setItem("customSession", JSON.stringify({
      company: customCompany ?? { name: companyName },
      role: form,
      isCustomCompany: source === "custom",
      knownCompanyId: companyParam ?? null,
    }));
    router.push("/interview/demo-session");
  }

  function handleBack() {
    if (source === "custom") router.push("/prep/custom-company");
    else router.push("/prep");
  }

  const stepLabel = source === "custom" ? "Step 2 of 2" : "Tell us about the role";

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <button onClick={handleBack} className="text-sm text-neutral-400 hover:text-[#0a0a0a] mb-8 flex items-center gap-1 transition-colors">
        ← Back
      </button>

      <div className="mb-10">
        <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-3">{stepLabel}</p>
        <h1 className="text-3xl font-bold text-[#0a0a0a] mb-2">
          {companyName ? `What role at ${companyName}?` : "Tell us about the role"}
        </h1>
        <p className="text-neutral-500 text-sm">We'll use this to shape the interview questions and style.</p>
      </div>

      <div className="space-y-6">
        {/* Role title */}
        <div>
          <label className="block text-sm font-semibold text-[#0a0a0a] mb-2">Role title</label>
          <input
            type="text"
            placeholder="e.g. Senior Software Engineer"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full text-sm px-4 py-3 border border-[#e5e5e5] rounded-lg focus:outline-none focus:border-[#0a0a0a] placeholder:text-neutral-400"
          />
        </div>

        {/* Responsibilities */}
        <div>
          <label className="block text-sm font-semibold text-[#0a0a0a] mb-2">What will you be doing day-to-day?</label>
          <textarea
            placeholder="Describe the responsibilities, team structure, and what success looks like in this role..."
            value={form.responsibilities}
            onChange={(e) => setForm({ ...form, responsibilities: e.target.value })}
            rows={4}
            className="w-full text-sm px-4 py-3 border border-[#e5e5e5] rounded-lg focus:outline-none focus:border-[#0a0a0a] placeholder:text-neutral-400 resize-none"
          />
        </div>

        {/* Skills */}
        <div>
          <label className="block text-sm font-semibold text-[#0a0a0a] mb-2">Key skills or technologies required</label>
          <input
            type="text"
            placeholder="e.g. Python, distributed systems, ML pipelines"
            value={form.skills}
            onChange={(e) => setForm({ ...form, skills: e.target.value })}
            className="w-full text-sm px-4 py-3 border border-[#e5e5e5] rounded-lg focus:outline-none focus:border-[#0a0a0a] placeholder:text-neutral-400"
          />
        </div>

        {/* Interview format */}
        <div>
          <label className="block text-sm font-semibold text-[#0a0a0a] mb-1">What type of interview are you expecting?</label>
          <p className="text-xs text-neutral-400 mb-3">Select all that apply</p>
          <div className="flex flex-wrap gap-2">
            {interviewFormats.map((f) => (
              <button
                key={f}
                onClick={() => toggleFormat(f)}
                className={`text-sm px-4 py-2 rounded-lg border transition-colors ${
                  form.formats.includes(f)
                    ? "border-[#0a0a0a] bg-[#0a0a0a] text-white"
                    : "border-[#e5e5e5] text-neutral-600 hover:border-neutral-300"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={handleStart}
        disabled={!isValid}
        className={`w-full mt-10 py-3 rounded-md font-semibold text-sm transition-colors ${
          isValid
            ? "bg-[#f5c518] text-[#0a0a0a] hover:bg-yellow-400 cursor-pointer"
            : "bg-[#e5e5e5] text-neutral-400 cursor-not-allowed"
        }`}
      >
        Start interview
      </button>
    </div>
  );
}

export default function CustomRolePage() {
  return (
    <Suspense>
      <CustomRoleForm />
    </Suspense>
  );
}
