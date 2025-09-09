"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { login, register as registerApi } from "@/lib/api";
import { signInSchema, type SignInValues, signUpSchema, type SignUpValues } from "@/lib/validation/auth";

export function useSignInForm() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = async (values: SignInValues) => {
    setIsLoading(true);
    setFormError(null);
    try {
      await login(values.email, values.password);
      router.push("/");
    } catch (err: any) {
      const status = err?.response?.status;
      const msg =
        status === 401
          ? "Invalid email or password"
          : err?.response?.data?.detail || err?.response?.data?.message || err?.message || "Login failed";
      setFormError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return { form, isLoading, formError, onSubmit };
}

export function useSignUpForm() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<SignUpValues>({
    resolver: zodResolver(signUpSchema),
    defaultValues: { email: "", password: "", passwordConfirm: "", terms: false },
  });

  const onSubmit = async (values: SignUpValues) => {
    setIsLoading(true);
    setFormError(null);
    try {
      await registerApi(values.email, values.password);
      router.push("/");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || err?.message || "Sign up failed";
      setFormError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return { form, isLoading, formError, onSubmit };
}


