"use client";

type DividerProps = { label?: string };

export function Divider({ label = "or" }: DividerProps) {
  return (
    <div className="relative">
      <div className="absolute inset-0 flex items-center">
        <span className="w-full border-t" />
      </div>
      <div className="relative flex justify-center text-xs">
        <span className="bg-background text-muted-foreground px-2 uppercase">
          {label}
        </span>
      </div>
    </div>
  );
}


