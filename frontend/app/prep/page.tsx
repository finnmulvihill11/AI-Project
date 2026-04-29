"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useUser } from "@clerk/nextjs";

type Role = {
  title: string;
  tags: string[];
  duration: string;
};

type Company = {
  id: string;
  name: string;
  logo: string | null;
  initial: string | null;
  color: string;
  roles: Role[];
};

const categories: { label: string; companies: Company[] }[] = [
  {
    label: "Big Tech",
    companies: [
      { id: "google", name: "Google", logo: "/logos/google.svg", initial: null, color: "#4285F4", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Behavioral"], duration: "45 min" },
        { title: "Data Scientist", tags: ["Coding", "Statistics", "Behavioral"], duration: "45 min" },
        { title: "Product Manager", tags: ["Product Sense", "Behavioral", "Estimation"], duration: "45 min" },
        { title: "Site Reliability Engineer", tags: ["Coding", "System Design", "On-call"], duration: "45 min" },
      ]},
      { id: "meta", name: "Meta", logo: "/logos/meta.svg", initial: null, color: "#0467DF", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Behavioral"], duration: "45 min" },
        { title: "Data Engineer", tags: ["Coding", "SQL", "System Design"], duration: "45 min" },
        { title: "Product Manager", tags: ["Product Sense", "Execution", "Behavioral"], duration: "45 min" },
        { title: "Research Engineer", tags: ["Coding", "ML", "Research"], duration: "45 min" },
      ]},
      { id: "apple", name: "Apple", logo: "/logos/apple.svg", initial: null, color: "#000000", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Behavioral"], duration: "45 min" },
        { title: "Machine Learning Engineer", tags: ["Coding", "ML", "System Design"], duration: "45 min" },
        { title: "Product Manager", tags: ["Product Sense", "Behavioral"], duration: "45 min" },
      ]},
      { id: "netflix", name: "Netflix", logo: "/logos/netflix.svg", initial: null, color: "#E50914", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Behavioral"], duration: "45 min" },
        { title: "Data Scientist", tags: ["Coding", "Statistics", "Behavioral"], duration: "45 min" },
        { title: "Product Manager", tags: ["Product Sense", "Behavioral"], duration: "45 min" },
      ]},
      { id: "amazon", name: "Amazon", logo: null, initial: "a", color: "#FF9900", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Leadership Principles"], duration: "45 min" },
        { title: "Data Scientist", tags: ["Coding", "Statistics", "Leadership Principles"], duration: "45 min" },
        { title: "Product Manager", tags: ["Product Sense", "Leadership Principles"], duration: "45 min" },
        { title: "Solutions Architect", tags: ["System Design", "Leadership Principles"], duration: "45 min" },
      ]},
    ],
  },
  {
    label: "Finance & Quant",
    companies: [
      { id: "jane-street", name: "Jane Street", logo: null, initial: "JS", color: "#1a1a2e", roles: [
        { title: "Software Engineer", tags: ["Coding", "OCaml", "Systems"], duration: "60 min" },
        { title: "Quantitative Trader", tags: ["Probability", "Mental Math", "Strategy"], duration: "60 min" },
        { title: "Quantitative Researcher", tags: ["Probability", "Statistics", "Coding"], duration: "60 min" },
      ]},
      { id: "stripe", name: "Stripe", logo: "/logos/stripe.svg", initial: null, color: "#635BFF", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Behavioral"], duration: "45 min" },
        { title: "Data Engineer", tags: ["Coding", "SQL", "System Design"], duration: "45 min" },
        { title: "Product Manager", tags: ["Product Sense", "Behavioral"], duration: "45 min" },
      ]},
      { id: "coinbase", name: "Coinbase", logo: "/logos/coinbase.svg", initial: null, color: "#0052FF", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Behavioral"], duration: "45 min" },
        { title: "Data Scientist", tags: ["Coding", "Statistics", "Behavioral"], duration: "45 min" },
        { title: "Product Manager", tags: ["Product Sense", "Behavioral"], duration: "45 min" },
      ]},
      { id: "palantir", name: "Palantir", logo: "/logos/palantir.svg", initial: null, color: "#101113", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Behavioral"], duration: "45 min" },
        { title: "Forward Deployed Engineer", tags: ["Coding", "Problem Solving", "Client Scenarios"], duration: "60 min" },
        { title: "Data Engineer", tags: ["Coding", "SQL", "System Design"], duration: "45 min" },
      ]},
    ],
  },
  {
    label: "Consumer & Growth",
    companies: [
      { id: "airbnb", name: "Airbnb", logo: "/logos/airbnb.svg", initial: null, color: "#FF5A5F", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Behavioral"], duration: "45 min" },
        { title: "Data Scientist", tags: ["Coding", "Statistics", "Behavioral"], duration: "45 min" },
        { title: "Product Manager", tags: ["Product Sense", "Behavioral"], duration: "45 min" },
      ]},
      { id: "uber", name: "Uber", logo: "/logos/uber.svg", initial: null, color: "#000000", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Behavioral"], duration: "45 min" },
        { title: "Data Scientist", tags: ["Coding", "Statistics", "Behavioral"], duration: "45 min" },
        { title: "Product Manager", tags: ["Product Sense", "Behavioral"], duration: "45 min" },
      ]},
      { id: "spotify", name: "Spotify", logo: "/logos/spotify.svg", initial: null, color: "#1ED760", roles: [
        { title: "Software Engineer", tags: ["Coding", "System Design", "Behavioral"], duration: "45 min" },
        { title: "Data Engineer", tags: ["Coding", "SQL", "System Design"], duration: "45 min" },
        { title: "Product Manager", tags: ["Product Sense", "Behavioral"], duration: "45 min" },
      ]},
    ],
  },
];

const allCompanies = categories.flatMap((c) => c.companies);

function CompanyLogo({ company, size }: { company: Company; size: number }) {
  if (company.logo) {
    return <Image src={company.logo} alt={company.name} width={size} height={size} />;
  }
  return (
    <span
      className="font-bold text-white flex items-center justify-center w-full h-full rounded-xl"
      style={{ backgroundColor: company.color, fontSize: size * 0.4 }}
    >
      {company.initial}
    </span>
  );
}

export default function PrepPage() {
  const router = useRouter();
  const { user } = useUser();
  const [step, setStep] = useState<1 | 2>(1);
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [roleSearch, setRoleSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const myCompanyIds = (user?.unsafeMetadata?.targetCompanies as string[] | undefined) ?? [];
  const myCompanies = myCompanyIds
    .map((id) => allCompanies.find((c) => c.id === id))
    .filter(Boolean)
    .filter((c) => c!.name.toLowerCase().includes(search.toLowerCase())) as Company[];
  const company = allCompanies.find((c) => c.id === selectedCompany) ?? null;

  const filteredCategories = categories.map((cat) => ({
    ...cat,
    companies: cat.companies.filter((c) =>
      c.name.toLowerCase().includes(search.toLowerCase())
    ),
  })).filter((cat) => cat.companies.length > 0);

  function handleSelectCompany(id: string) {
    setSelectedCompany(id);
    setSelectedRole(null);
    setStep(2);
  }

  function handleBack() {
    setStep(1);
    setSelectedRole(null);
    setRoleSearch("");
  }

  async function handleStart() {
    if (!selectedCompany || !selectedRole) return;
    setLoading(true);
    setStartError(null);

    // Request mic permission here so there's no jarring popup mid-interview
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(t => t.stop());
    } catch {
      setStartError("Microphone access is required. Please allow it and try again.");
      setLoading(false);
      return;
    }

    const company = allCompanies.find(c => c.id === selectedCompany)!;
    localStorage.setItem("pendingSession", JSON.stringify({
      company: company.name,
      role: selectedRole,
    }));

    const companyId = selectedCompany.replace(/-/g, "_");
    const roleId    = selectedRole.toLowerCase().replace(/[\s()]+/g, "_").replace(/_+$/, "");

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"}/sessions`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ company_id: companyId, role_id: roleId, round: "phone_screen" }),
        }
      );
      if (!res.ok) throw new Error();
      const { session_id } = await res.json();
      router.push(`/interview/${session_id}`);
    } catch {
      setStartError("Couldn't connect to the interview server. Make sure the backend is running on port 8000.");
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-[#0a0a0a] mb-2">Choose your interview</h1>
        <p className="text-neutral-500 text-sm">Select a company and role to begin.</p>
      </div>

      <div className="inline-flex items-center gap-2 bg-[#f5c518]/20 border border-[#f5c518] text-[#0a0a0a] text-xs font-medium px-3 py-1.5 rounded-full mb-10">
        <span className="w-1.5 h-1.5 rounded-full bg-[#f5c518]" />
        You have 1 free interview remaining
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-3 mb-10">
        <div className="flex items-center gap-2">
          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step >= 1 ? "bg-[#0a0a0a] text-white" : "bg-[#e5e5e5] text-neutral-400"}`}>1</span>
          <span className={`text-sm font-medium ${step === 1 ? "text-[#0a0a0a]" : "text-neutral-400"}`}>Company</span>
        </div>
        <div className="w-8 h-px bg-[#e5e5e5]" />
        <div className="flex items-center gap-2">
          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step === 2 ? "bg-[#0a0a0a] text-white" : "bg-[#e5e5e5] text-neutral-400"}`}>2</span>
          <span className={`text-sm font-medium ${step === 2 ? "text-[#0a0a0a]" : "text-neutral-400"}`}>Role</span>
        </div>
      </div>

      {/* Step 1 — Company grid */}
      {step === 1 && (
        <div className="space-y-8">
          <input
            type="text"
            placeholder="Search companies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full text-sm px-4 py-2.5 border border-[#e5e5e5] rounded-lg focus:outline-none focus:border-[#0a0a0a] placeholder:text-neutral-400"
          />
          {myCompanies.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest">My Companies</p>
                <button onClick={() => router.push("/settings")} className="text-xs text-neutral-400 hover:text-[#0a0a0a] transition-colors">Edit</button>
              </div>
              <div className="flex flex-wrap gap-3">
                {myCompanies.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => handleSelectCompany(c.id)}
                    className="group w-32 border border-[#e5e5e5] rounded-xl p-4 flex flex-col items-center gap-3 hover:border-[#0a0a0a] hover:shadow-sm transition-all bg-white"
                  >
                    <div className="w-11 h-11 rounded-xl border border-[#e5e5e5] flex items-center justify-center bg-white overflow-hidden">
                      <CompanyLogo company={c} size={26} />
                    </div>
                    <span className="text-xs font-semibold text-[#0a0a0a] text-center leading-tight">{c.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {filteredCategories.length === 0 && (
            <p className="text-sm text-neutral-400 mb-2">No companies found.</p>
          )}
          {filteredCategories.map((cat) => (
            <div key={cat.label}>
              <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-4">{cat.label}</p>
              <div className="flex flex-wrap gap-3">
                {(cat as typeof categories[0]).companies.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => handleSelectCompany(c.id)}
                    className="group w-32 border border-[#e5e5e5] rounded-xl p-4 flex flex-col items-center gap-3 hover:border-[#0a0a0a] hover:shadow-sm transition-all bg-white"
                  >
                    <div className="w-11 h-11 rounded-xl border border-[#e5e5e5] flex items-center justify-center bg-white overflow-hidden">
                      <CompanyLogo company={c} size={26} />
                    </div>
                    <span className="text-xs font-semibold text-[#0a0a0a] text-center leading-tight">{c.name}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
          {/* Company not listed */}
          <div>
            <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest mb-4">Other</p>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => router.push("/prep/custom-company")}
                className="group w-32 border border-dashed border-[#e5e5e5] rounded-xl p-4 flex flex-col items-center gap-3 hover:border-neutral-300 hover:shadow-sm transition-all bg-white"
              >
                <div className="w-11 h-11 rounded-xl border border-dashed border-[#e5e5e5] flex items-center justify-center bg-white text-neutral-400 text-xl group-hover:border-neutral-300 transition-colors">
                  +
                </div>
                <span className="text-xs font-semibold text-neutral-400 text-center leading-tight group-hover:text-neutral-600 transition-colors">Not listed?</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 2 — Role */}
      {step === 2 && company && (
        <div>
          <button onClick={handleBack} className="text-sm text-neutral-400 hover:text-[#0a0a0a] mb-6 flex items-center gap-1 transition-colors">
            ← Back
          </button>

          {/* Company header */}
          <div className="flex items-center gap-4 p-5 border border-[#e5e5e5] rounded-xl mb-6 bg-[#fafafa]">
            <div className="w-12 h-12 rounded-xl border border-[#e5e5e5] flex items-center justify-center bg-white overflow-hidden shrink-0">
              <CompanyLogo company={company} size={28} />
            </div>
            <div>
              <p className="font-semibold text-[#0a0a0a]">{company.name}</p>
              <p className="text-xs text-neutral-400 mt-0.5">{company.roles.length} roles available</p>
            </div>
          </div>

          {/* Role search */}
          <input
            type="text"
            placeholder="Search roles..."
            value={roleSearch}
            onChange={(e) => setRoleSearch(e.target.value)}
            className="w-full text-sm px-4 py-2.5 border border-[#e5e5e5] rounded-lg focus:outline-none focus:border-[#0a0a0a] placeholder:text-neutral-400 mb-4"
          />

          {/* Role cards */}
          <div className="space-y-3 mb-8">
            {company.roles.filter((r) => r.title.toLowerCase().includes(roleSearch.toLowerCase())).length === 0 && (
              <p className="text-sm text-neutral-400">No roles found.</p>
            )}
            {company.roles.filter((r) => r.title.toLowerCase().includes(roleSearch.toLowerCase())).map((role) => (
              <button
                key={role.title}
                onClick={() => setSelectedRole(role.title)}
                className={`w-full text-left border rounded-xl px-5 py-4 transition-all ${
                  selectedRole === role.title
                    ? "border-[#0a0a0a] bg-white shadow-sm"
                    : "border-[#e5e5e5] hover:border-neutral-300 bg-white"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <p className="font-semibold text-[#0a0a0a] text-sm mb-2">{role.title}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {role.tags.map((tag) => (
                        <span key={tag} className="text-xs px-2 py-0.5 bg-[#f5f5f5] text-neutral-500 rounded-md">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <span className="text-xs text-neutral-400">{role.duration}</span>
                    {selectedRole === role.title && (
                      <span className="w-2 h-2 rounded-full bg-[#f5c518]" />
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Role not listed */}
          <button
            onClick={() => router.push(`/prep/custom-role?company=${selectedCompany}`)}
            className="group w-full text-left border border-dashed border-[#e5e5e5] rounded-xl px-5 py-4 mb-4 transition-all hover:border-neutral-300 bg-white"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <p className="font-semibold text-neutral-400 text-sm mb-2 group-hover:text-neutral-600 transition-colors">Not listed?</p>
                <div className="flex flex-wrap gap-1.5">
                  <span className="text-xs px-2 py-0.5 bg-[#f5f5f5] text-neutral-400 rounded-md">Custom</span>
                </div>
              </div>
              <div className="flex flex-col items-end gap-2 shrink-0">
                <span className="text-xs text-neutral-300">—</span>
              </div>
            </div>
          </button>

          <button
            onClick={handleStart}
            disabled={!selectedRole || loading}
            className={`w-full py-3 rounded-md font-semibold text-sm transition-colors ${
              selectedRole && !loading
                ? "bg-[#f5c518] text-[#0a0a0a] hover:bg-yellow-400 cursor-pointer"
                : "bg-[#e5e5e5] text-neutral-400 cursor-not-allowed"
            }`}
          >
            {loading ? "Starting..." : "Start interview"}
          </button>
          {startError && (
            <p className="text-xs text-red-500 mt-2 text-center">{startError}</p>
          )}
        </div>
      )}
    </div>
  );
}
