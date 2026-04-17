"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const industries = ["Technology", "Finance & Quant", "Healthcare", "Defense", "Consumer", "E-commerce", "Media", "Other"];
const stages = ["Early-stage startup", "Growth-stage startup", "Mid-size company", "Enterprise / Public company"];

export default function CustomCompanyPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    description: "",
    industry: "",
    stage: "",
  });

  const isValid = form.name.trim() && form.description.trim() && form.industry && form.stage;

  function handleNext() {
    if (!isValid) return;
    localStorage.setItem("customCompany", JSON.stringify(form));
    router.push("/prep/custom-role?source=custom");
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <button onClick={() => router.push("/prep")} className="text-sm text-neutral-400 hover:text-[#0a0a0a] mb-8 flex items-center gap-1 transition-colors">
        ← Back
      </button>

      <div className="mb-10">
        <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-3">Step 1 of 2</p>
        <h1 className="text-3xl font-bold text-[#0a0a0a] mb-2">Tell us about the company</h1>
        <p className="text-neutral-500 text-sm">We'll use this to tailor your interview to the company's culture and expectations.</p>
      </div>

      <div className="space-y-6">
        {/* Company name */}
        <div>
          <label className="block text-sm font-semibold text-[#0a0a0a] mb-2">Company name</label>
          <input
            type="text"
            placeholder="e.g. Anthropic"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full text-sm px-4 py-3 border border-[#e5e5e5] rounded-lg focus:outline-none focus:border-[#0a0a0a] placeholder:text-neutral-400"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-semibold text-[#0a0a0a] mb-2">What does the company do?</label>
          <textarea
            placeholder="Describe the company's product, mission, and what makes it unique..."
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={4}
            className="w-full text-sm px-4 py-3 border border-[#e5e5e5] rounded-lg focus:outline-none focus:border-[#0a0a0a] placeholder:text-neutral-400 resize-none"
          />
        </div>

        {/* Industry */}
        <div>
          <label className="block text-sm font-semibold text-[#0a0a0a] mb-2">Industry</label>
          <div className="flex flex-wrap gap-2">
            {industries.map((ind) => (
              <button
                key={ind}
                onClick={() => setForm({ ...form, industry: ind })}
                className={`text-sm px-4 py-2 rounded-lg border transition-colors ${
                  form.industry === ind
                    ? "border-[#0a0a0a] bg-[#0a0a0a] text-white"
                    : "border-[#e5e5e5] text-neutral-600 hover:border-neutral-300"
                }`}
              >
                {ind}
              </button>
            ))}
          </div>
        </div>

        {/* Stage */}
        <div>
          <label className="block text-sm font-semibold text-[#0a0a0a] mb-2">Company stage</label>
          <div className="space-y-2">
            {stages.map((stage) => (
              <button
                key={stage}
                onClick={() => setForm({ ...form, stage })}
                className={`w-full text-left text-sm px-4 py-3 rounded-lg border transition-colors flex items-center justify-between ${
                  form.stage === stage
                    ? "border-[#0a0a0a] bg-[#f5f5f5]"
                    : "border-[#e5e5e5] text-neutral-600 hover:border-neutral-300"
                }`}
              >
                {stage}
                {form.stage === stage && <span className="w-2 h-2 rounded-full bg-[#f5c518]" />}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={handleNext}
        disabled={!isValid}
        className={`w-full mt-10 py-3 rounded-md font-semibold text-sm transition-colors ${
          isValid
            ? "bg-[#f5c518] text-[#0a0a0a] hover:bg-yellow-400 cursor-pointer"
            : "bg-[#e5e5e5] text-neutral-400 cursor-not-allowed"
        }`}
      >
        Next — Tell us about the role
      </button>
    </div>
  );
}
