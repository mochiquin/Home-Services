"use client";

import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthSidebar } from "@/components/auth/AuthSidebar";
import { AuthHeader } from "@/components/auth/AuthHeader";
import { Divider } from "@/components/common/Divider";
import { SocialAuthButtons } from "@/components/auth/SocialAuthButtons";
import { TermsCheckbox } from "@/components/auth/TermsCheckbox";
import { SubmitButton } from "@/components/common/SubmitButton";
import { useSignUpForm } from "@/lib/hooks/useAuthForms";

export default function SignUpPage() {
  const { form, isLoading, formError, onSubmit } = useSignUpForm();
  const { register, handleSubmit, setValue, watch, formState: { errors } } = form;

  const termsChecked = watch("terms");

  return (
    <div className="bg-background md:flex md:min-h-screen">
      <AuthSidebar />

      {/* Main sign up form container */}
      <div className="flex items-center justify-center md:w-[60%]">
        <div className="w-full max-w-sm px-6 py-16 md:p-0">
          {/* Header section */}
          <AuthHeader
            title="Create an account"
            description="Let's get started. Fill in the details below to create your account."
          />

          {/* Form fields */}
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
              <Label htmlFor="password">Password</Label>
              <Input id="password" placeholder="Password" type="password" {...register("password")} />
              {errors.password && (
                <p className="text-[0.8rem] font-medium text-destructive">{errors.password.message}</p>
              )}
            </div>

            {/* Confirm password */}
            <div className="space-y-2">
              <Label htmlFor="passwordConfirm">Confirm password</Label>
              <Input
                id="passwordConfirm"
                placeholder="Confirm password"
                type="password"
                {...register("passwordConfirm")}
              />
              {errors.passwordConfirm && (
                <p className="text-[0.8rem] font-medium text-destructive">{errors.passwordConfirm.message}</p>
              )}
            </div>

            {/* Terms checkbox */}
            <TermsCheckbox
              checked={termsChecked}
              onCheckedChange={(v) => setValue("terms", v, { shouldValidate: true })}
              errorMessage={errors.terms?.message}
            />

            <SubmitButton className="w-full" isLoading={isLoading}>
              Sign up
            </SubmitButton>
          </form>

          {/* Sign up button and social login */}
          <Divider label="or sign in with" />

          <div className="mt-6">
            <SocialAuthButtons />
          </div>

          {/* Sign in link */}
          <p className="text-muted-foreground text-center text-sm mt-6">
            Already have an account?{" "}
            <Link className="text-foreground underline" href="/sign-in">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
