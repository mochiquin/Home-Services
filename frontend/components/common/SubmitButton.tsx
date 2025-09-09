"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";

type SubmitButtonProps = React.ComponentProps<typeof Button> & {
  isLoading?: boolean;
};

export function SubmitButton({ isLoading, children, disabled, ...props }: SubmitButtonProps) {
  return (
    <Button {...props} disabled={disabled || isLoading}>
      {isLoading ? "Loading..." : children}
    </Button>
  );
}


