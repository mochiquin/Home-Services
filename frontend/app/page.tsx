"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function Home() {
  const [message, setMessage] = useState<string>("Loading...");
  const [loading, setLoading] = useState<boolean>(false);

  async function fetchHealth() {
    try {
      setLoading(true);
      const res = await apiClient.get("/health/");
      setMessage(typeof res.data === "string" ? res.data : JSON.stringify(res.data));
    } catch (e: any) {
      setMessage(e?.message ?? "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <main className="min-h-screen p-8 flex items-center justify-center">
      <Card className="p-6 w-full max-w-xl space-y-4">
        <div className="text-xl font-semibold">Home Services Frontend</div>
        <div className="text-sm text-muted-foreground">Health Check:</div>
        <pre className="rounded bg-muted p-4 text-sm overflow-auto">{message}</pre>
        <Button onClick={fetchHealth} disabled={loading}>
          {loading ? "Checking..." : "Re-run Health Check"}
        </Button>
      </Card>
    </main>
  );
}
