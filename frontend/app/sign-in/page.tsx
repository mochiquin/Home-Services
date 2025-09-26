"use client";

import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthSidebar } from "@/components/auth/AuthSidebar";
import { AuthHeader } from "@/components/auth/AuthHeader";
import { Divider } from "@/components/common/Divider";
import { SocialAuthButtons } from "@/components/auth/SocialAuthButtons";
import { SubmitButton } from "@/components/common/SubmitButton";
import { useSignInForm } from "@/lib/hooks/useAuthForms";

export default function SignInPage() {
  const { form, isLoading, formError, onSubmit } = useSignInForm();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = form;

  return (
    <div className="bg-background md:flex md:min-h-screen">
      <AuthSidebar />

      {/* Right side - Sign-in form */}
      <div className="flex items-center justify-center md:w-[60%]">
        <div className="w-full max-w-sm px-6 py-16 md:p-0">
          {/* Header section */}
          <AuthHeader
            title="Sign in"
            description="Log in to unlock tailored content and stay connected with your community."
          />

          {/* Sign-in form */}
          <form onSubmit={handleSubmit(onSubmit)} className="mb-6 space-y-4">
            {formError ? (
              <p className="text-[0.8rem] font-medium text-destructive">{formError}</p>
            ) : null}
            {/* Email input */}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" placeholder="Email" type="email" {...register("email")} />
              {errors.email && (
                <p className="text-[0.8rem] font-medium text-destructive">{errors.email.message}</p>
              )}
            </div>

            {/* Password input */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link
                  href="#"
                  className="text-muted-foreground hover:text-foreground text-sm underline"
                >
                  Forgot password?
                </Link>
              </div>
              <Input id="password" placeholder="Password" type="password" {...register("password")} />
              {errors.password && (
                <p className="text-[0.8rem] font-medium text-destructive">{errors.password.message}</p>
              )}
            </div>

            <SubmitButton className="w-full" isLoading={isLoading}>
              Sign in
            </SubmitButton>
          </form>

          <Divider label="or sign in with" />

          {/* Social login buttons */}
          <div className="mt-6">
            <SocialAuthButtons />
          </div>

          {/* Sign up link */}
          <p className="text-muted-foreground text-center text-sm mt-6">
            Don't have an account?{" "}
            <Link className="text-foreground underline" href="/sign-up">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
