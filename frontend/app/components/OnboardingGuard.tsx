"use client";

import { useUser } from "@clerk/nextjs";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";

export default function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoaded, isSignedIn } = useUser();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    const complete = user?.unsafeMetadata?.onboardingComplete;
    if (!complete && pathname !== "/onboarding") router.replace("/onboarding");
    if (complete && pathname === "/onboarding") router.replace("/prep");
  }, [isLoaded, isSignedIn, user, pathname, router]);

  return <>{children}</>;
}
