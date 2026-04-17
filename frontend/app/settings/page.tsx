"use client";

import { useState, useEffect } from "react";
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

export default function SettingsPage() {
  const router = useRouter();
  const { user, isLoaded } = useUser();
  const [targetCompanies, setTargetCompanies] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isLoaded && user) {
      const stored = user.unsafeMetadata?.targetCompanies as string[] | undefined;
      if (stored) setTargetCompanies(stored);
    }
  }, [isLoaded, user]);

  function toggleCompany(id: string) {
    setSaved(false);
    setTargetCompanies((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  }

  async function handleSave() {
    if (!user) return;
    setSaving(true);
    await user.update({
      unsafeMetadata: { ...user.unsafeMetadata, targetCompanies },
    });
    setSaving(false);
    setSaved(true);
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <button onClick={() => router.push("/prep")} className="text-sm text-neutral-400 hover:text-[#0a0a0a] mb-8 flex items-center gap-1 transition-colors">
        ← Back to prep
      </button>

      <div className="mb-10">
        <h1 className="text-3xl font-bold text-[#0a0a0a] mb-2">Target companies</h1>
        <p className="text-neutral-500 text-sm">These appear at the top of your prep page under "My Companies".</p>
      </div>

      <div className="flex flex-wrap gap-3 mb-10">
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

      <button
        onClick={handleSave}
        disabled={saving}
        className="px-8 py-3 rounded-md font-semibold text-sm bg-[#f5c518] text-[#0a0a0a] hover:bg-yellow-400 transition-colors cursor-pointer disabled:opacity-50"
      >
        {saving ? "Saving..." : saved ? "Saved!" : "Save changes"}
      </button>
    </div>
  );
}
