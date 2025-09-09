"use client";

import { Logo } from "@/components/common/Logo";

type AuthHeaderProps = {
  title: string;
  description?: string;
  showLogoOnMobile?: boolean;
};

export function AuthHeader({ title, description, showLogoOnMobile = true }: AuthHeaderProps) {
  return (
    <div className="mb-6 space-y-6">
      {showLogoOnMobile && <Logo className="block h-10 w-10 md:hidden md:h-12 md:w-12" />}
      <div className="flex flex-col gap-y-3">
        <h1 className="text-2xl font-bold md:text-3xl">{title}</h1>
        {description ? (
          <p className="text-muted-foreground text-sm">{description}</p>
        ) : null}
      </div>
    </div>
  );
}


