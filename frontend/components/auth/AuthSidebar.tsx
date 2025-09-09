"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

type AuthSidebarProps = {
  className?: string;
  theme?: "light" | "dark" | "inverse";
};

export function AuthSidebar({ className, theme = "inverse" }: AuthSidebarProps) {
  const themeClasses =
    theme === "inverse"
      ? "bg-background text-foreground dark:bg-foreground dark:text-background"
      : theme === "dark"
      ? "bg-foreground text-background"
      : "bg-background text-foreground";

  return (
    <div className={cn("hidden min-h-full w-[40%] flex-col-reverse p-12 md:flex", themeClasses, className)}>
      <div className="flex h-full flex-col justify-between gap-y-12">
        <div className="max-w-xl">
          <Avatar className="mb-6 h-12 w-12">
            <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
            <AvatarFallback>ST</AvatarFallback>
          </Avatar>
          <p className="mb-6 text-lg opacity-90">
            "Shadcn UI Kit for Figma has completely transformed our design process. It's
            incredibly intuitive and saves us so much time. The components are beautifully
            crafted and customizable."
          </p>
        </div>
        <div>
          <p className="font-semibold">Sarah Thompson</p>
          <p className="opacity-80">Lead UX Designer at BrightWave Solutions</p>
        </div>
      </div>
    </div>
  );
}


