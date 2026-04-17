import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="min-h-[calc(100vh-56px)] flex items-center justify-center px-6">
      <SignIn />
    </div>
  );
}
