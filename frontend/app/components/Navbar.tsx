"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth, useUser, useClerk } from "@clerk/nextjs";
import { useState, useRef, useEffect } from "react";

const navLinks = [
  { href: "/prep", label: "Interview Prep" },
  { href: "/performance", label: "My Performance" },
];

const aboutLinks = [
  { href: "/about#how-it-works", label: "How it works", description: "The mechanics behind prep" },
  { href: "/about#companies",    label: "Companies",    description: "Supported companies and question types" },
  { href: "/about#team",         label: "The Team",     description: "The people building prep" },
  { href: "/about#pricing",      label: "Pricing",      description: "Free trial and plan details" },
];

function AboutDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const isActive = pathname?.startsWith("/about");

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1 text-sm transition-colors ${
          isActive ? "text-[#0a0a0a] font-medium" : "text-neutral-500 hover:text-[#0a0a0a]"
        }`}
      >
        About
        <svg
          className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`}
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
        >
          <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="absolute top-full right-0 mt-2.5 w-64 bg-white border border-[#e5e5e5] rounded-lg shadow-sm py-1.5 z-50">
          {aboutLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              className="flex flex-col px-4 py-2.5 hover:bg-[#f5f5f5] transition-colors"
            >
              <span className="text-sm font-medium text-[#0a0a0a]">{link.label}</span>
              <span className="text-xs text-neutral-400 mt-0.5">{link.description}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function UserAvatar() {
  const { user } = useUser();
  const { signOut } = useClerk();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const first = user?.firstName?.[0] ?? "";
  const last = user?.lastName?.[0] ?? "";
  const initials = (first + last).toUpperCase() || user?.emailAddresses[0]?.emailAddress[0].toUpperCase() || "?";

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="h-8 px-2 min-w-8 rounded-full bg-[#0a0a0a] text-white text-xs font-semibold flex items-center justify-center hover:bg-neutral-700 transition-colors tracking-wide"
      >
        {initials}
      </button>
      {open && (
        <div className="absolute top-full right-0 mt-2.5 w-44 bg-white border border-[#e5e5e5] rounded-lg shadow-sm py-1.5 z-50">
          <button
            onClick={() => { setOpen(false); router.push("/settings"); }}
            className="w-full text-left px-4 py-2.5 text-sm text-[#0a0a0a] hover:bg-[#f5f5f5] transition-colors"
          >
            Settings
          </button>
          <div className="border-t border-[#e5e5e5] my-1" />
          <button
            onClick={() => signOut({ redirectUrl: "/" })}
            className="w-full text-left px-4 py-2.5 text-sm text-neutral-500 hover:bg-[#f5f5f5] transition-colors"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export default function Navbar() {
  const pathname = usePathname();
  const { isSignedIn } = useAuth();
  const isInterview = pathname?.startsWith("/interview");

  if (isInterview) return null;

  return (
    <header className="border-b border-[#e5e5e5] bg-white sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold tracking-tight text-[#0a0a0a]">
          prep
        </Link>

        <nav className="flex items-center gap-8">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm transition-colors ${
                pathname === link.href
                  ? "text-[#0a0a0a] font-medium"
                  : "text-neutral-500 hover:text-[#0a0a0a]"
              }`}
            >
              {link.label}
            </Link>
          ))}
          <AboutDropdown />
        </nav>

        <div className="flex items-center gap-3">
          {isSignedIn ? (
            <UserAvatar />
          ) : (
            <>
              <Link
                href="/sign-in"
                className="text-sm text-neutral-500 hover:text-[#0a0a0a] transition-colors"
              >
                Sign in
              </Link>
              <Link
                href="/sign-up"
                className="text-sm bg-[#0a0a0a] text-white px-4 py-2 rounded-md hover:bg-neutral-800 transition-colors"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
