'use client'

import { Toaster } from "sonner";
import React from "react";

export function Providers({ children }: { children: React.ReactNode }) {
	return (
		<>
			{children}
			<Toaster richColors position="top-right" closeButton />
		</>
	);
}
