"use client";

import Link from "next/link";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

type TermsCheckboxProps = {
  id?: string;
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  errorMessage?: string;
};

export function TermsCheckbox({ id = "terms", checked, onCheckedChange, errorMessage }: TermsCheckboxProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center space-x-2">
        <Checkbox id={id} checked={checked} onCheckedChange={(v) => onCheckedChange?.(!!v)} />
      <Label htmlFor={id} className="text-sm font-normal">
        I agree to the{" "}
        <Link href="#" className="text-foreground underline">
          Terms & Conditions
        </Link>
      </Label>
      </div>
      {errorMessage ? (
        <p className="text-[0.8rem] font-medium text-destructive">{errorMessage}</p>
      ) : null}
    </div>
  );
}


