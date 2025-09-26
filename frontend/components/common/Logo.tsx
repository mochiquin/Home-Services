"use client";

import * as React from "react";

export function Logo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" {...props}>
      <circle cx="12" cy="12" r="10" fill="currentColor" />
    </svg>
  );
}


