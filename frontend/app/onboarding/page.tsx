"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import Image from "next/image";

const allCompanies = [
  { id: "google",     name: "Google",     logo: "/logos/google.svg",   color: "#4285F4" },
  { id: "meta",       name: "Meta",       logo: "/logos/meta.svg",     color: "#0467DF" },
  { id: "apple",      name: "Apple",      logo: "/logos/apple.svg",    color: "#000000" },
  { id: "netflix",    name: "Netflix",    logo: "/logos/netflix.svg",  color: "#E50914" },
  { id: "amazon",     name: "Amazon",     logo: null,                  color: "#FF9900" },
  { id: "jane-street",name: "Jane Street",logo: null,                  color: "#1a1a2e" },
  { id: "stripe",     name: "Stripe",     logo: "/logos/stripe.svg",   color: "#635BFF" },
  { id: "coinbase",   name: "Coinbase",   logo: "/logos/coinbase.svg", color: "#0052FF" },
  { id: "palantir",   name: "Palantir",   logo: "/logos/palantir.svg", color: "#101113" },
  { id: "airbnb",     name: "Airbnb",     logo: "/logos/airbnb.svg",   color: "#FF5A5F" },
  { id: "uber",       name: "Uber",       logo: "/logos/uber.svg",     color: "#000000" },
  { id: "spotify",    name: "Spotify",    logo: "/logos/spotify.svg",  color: "#1ED760" },
];

const experienceLevels = ["New Grad", "1–3 years", "3–5 years", "5+ years"];
const timelines = ["This week", "1–2 weeks", "Within a month", "3+ months"];
const roleTypes = ["Software Engineer", "Product Manager", "Data Scientist", "Quant / Finance", "Other"];

const STEPS = ["Companies", "Experience", "Timeline", "Role"];

export default function OnboardingPage() {
  const router = useRouter();
  const { user } = useUser();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);

  const [targetCompanies, setTargetCompanies] = useState<string[]>([]);
  const [experience, setExperience] = useState("");
  const [timeline, setTimeline] = useState("");
  const [roleType, setRoleType] = useState("");

  function toggleCompany(id: string) {
    setTargetCompanies((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  }

  async function handleFinish() {
    if (!user) return;
    setSaving(true);
    await user.update({
      unsafeMetadata: {
        ...user.unsafeMetadata,
        onboardingComplete: true,
        targetCompanies,
        experience,
        timeline,
        roleType,
      },
    });
    router.replace("/prep");
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      {/* Header */}
      <div className="mb-10">
        <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-3">
          Step {step + 1} of {STEPS.length}
        </p>
        <div className="flex gap-1.5 mb-8">
          {STEPS.map((_, i) => (
            <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${i <= step ? "bg-[#f5c518]" : "bg-[#e5e5e5]"}`} />
          ))}
        </div>

        {step === 0 && (
          <>
            <h1 className="text-3xl font-bold text-[#0a0a0a] mb-2">Which companies are you targeting?</h1>
            <p className="text-neutral-500 text-sm">Select all that apply — we'll show these first on your prep page.</p>
          </>
        )}
        {step === 1 && (
          <>
            <h1 className="text-3xl font-bold text-[#0a0a0a] mb-2">How much experience do you have?</h1>
            <p className="text-neutral-500 text-sm">We'll use this to calibrate interview difficulty.</p>
          </>
        )}
        {step === 2 && (
          <>
            <h1 className="text-3xl font-bold text-[#0a0a0a] mb-2">When is your interview?</h1>
            <p className="text-neutral-500 text-sm">Helps us understand how much prep time you have.</p>
          </>
        )}
        {step === 3 && (
          <>
            <h1 className="text-3xl font-bold text-[#0a0a0a] mb-2">What role are you going for?</h1>
            <p className="text-neutral-500 text-sm">We'll prioritize the most relevant question types.</p>
          </>
        )}
      </div>

      {/* Step 0 — Companies */}
      {step === 0 && (
        <div className="flex flex-wrap gap-3">
          {allCompanies.map((c) => {
            const selected = targetCompanies.includes(c.id);
            return (
              <button
                key={c.id}
                onClick={() => toggleCompany(c.id)}
                className={`w-32 border rounded-xl p-4 flex flex-col items-center gap-3 transition-all ${
                  selected ? "border-[#0a0a0a] bg-[#f5f5f5] shadow-sm" : "border-[#e5e5e5] bg-white hover:border-neutral-300"
                }`}
              >
                <div className="w-11 h-11 rounded-xl border border-[#e5e5e5] flex items-center justify-center bg-white overflow-hidden">
                  {c.logo ? (
                    <Image src={c.logo} alt={c.name} width={26} height={26} />
                  ) : (
                    <span className="font-bold text-white flex items-center justify-center w-full h-full rounded-xl text-xs" style={{ backgroundColor: c.color }}>
                      {c.id === "amazon" ? "a" : "JS"}
                    </span>
                  )}
                </div>
                <span className="text-xs font-semibold text-[#0a0a0a] text-center leading-tight">{c.name}</span>
                {selected && <span className="w-2 h-2 rounded-full bg-[#f5c518]" />}
              </button>
            );
          })}
        </div>
      )}

      {/* Step 1 — Experience */}
      {step === 1 && (
        <div className="space-y-3">
          {experienceLevels.map((level) => (
            <button
              key={level}
              onClick={() => setExperience(level)}
              className={`w-full text-left border rounded-xl px-5 py-4 flex items-center justify-between transition-colors ${
                experience === level ? "border-[#0a0a0a] bg-[#f5f5f5]" : "border-[#e5e5e5] hover:border-neutral-300"
              }`}
            >
              <span className="font-medium text-[#0a0a0a]">{level}</span>
              {experience === level && <span className="w-2 h-2 rounded-full bg-[#f5c518]" />}
            </button>
          ))}
        </div>
      )}

      {/* Step 2 — Timeline */}
      {step === 2 && (
        <div className="space-y-3">
          {timelines.map((t) => (
            <button
              key={t}
              onClick={() => setTimeline(t)}
              className={`w-full text-left border rounded-xl px-5 py-4 flex items-center justify-between transition-colors ${
                timeline === t ? "border-[#0a0a0a] bg-[#f5f5f5]" : "border-[#e5e5e5] hover:border-neutral-300"
              }`}
            >
              <span className="font-medium text-[#0a0a0a]">{t}</span>
              {timeline === t && <span className="w-2 h-2 rounded-full bg-[#f5c518]" />}
            </button>
          ))}
        </div>
      )}

      {/* Step 3 — Role type */}
      {step === 3 && (
        <div className="space-y-3">
          {roleTypes.map((r) => (
            <button
              key={r}
              onClick={() => setRoleType(r)}
              className={`w-full text-left border rounded-xl px-5 py-4 flex items-center justify-between transition-colors ${
                roleType === r ? "border-[#0a0a0a] bg-[#f5f5f5]" : "border-[#e5e5e5] hover:border-neutral-300"
              }`}
            >
              <span className="font-medium text-[#0a0a0a]">{r}</span>
              {roleType === r && <span className="w-2 h-2 rounded-full bg-[#f5c518]" />}
            </button>
          ))}
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between mt-10">
        {step > 0 ? (
          <button onClick={() => setStep(step - 1)} className="text-sm text-neutral-400 hover:text-[#0a0a0a] transition-colors">
            ← Back
          </button>
        ) : <div />}

        {step < STEPS.length - 1 ? (
          <button
            onClick={() => setStep(step + 1)}
            disabled={step === 0 && targetCompanies.length === 0}
            className={`px-8 py-3 rounded-md font-semibold text-sm transition-colors ${
              step === 0 && targetCompanies.length === 0
                ? "bg-[#e5e5e5] text-neutral-400 cursor-not-allowed"
                : "bg-[#f5c518] text-[#0a0a0a] hover:bg-yellow-400 cursor-pointer"
            }`}
          >
            Next
          </button>
        ) : (
          <button
            onClick={handleFinish}
            disabled={!roleType || saving}
            className={`px-8 py-3 rounded-md font-semibold text-sm transition-colors ${
              roleType && !saving
                ? "bg-[#f5c518] text-[#0a0a0a] hover:bg-yellow-400 cursor-pointer"
                : "bg-[#e5e5e5] text-neutral-400 cursor-not-allowed"
            }`}
          >
            {saving ? "Saving..." : "Get started"}
          </button>
        )}
      </div>
    </div>
  );
}
