import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-[calc(100vh-56px)] flex items-center justify-center px-6">
      <SignUp />
    </div>
  );
}
