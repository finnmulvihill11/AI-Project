import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";
import Navbar from "./components/Navbar";
import OnboardingGuard from "./components/OnboardingGuard";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "prep",
  description: "AI-powered mock technical interviews",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full`}>
        <body className="min-h-full flex flex-col bg-white text-[#0a0a0a] antialiased">
          <Navbar />
          <OnboardingGuard>
            <main className="flex-1">{children}</main>
          </OnboardingGuard>
        </body>
      </html>
    </ClerkProvider>
  );
}
