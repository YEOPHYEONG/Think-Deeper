// src/app/page.tsx

"use client";

import { useState } from "react";
import { createSession } from "@/lib/api";
import { TopicInput } from "@/components/TopicInput";
import { TurnExchange } from "@/components/TurnExchange";

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  const handleStart = async (topic: string) => {
    const id = await createSession(topic);
    setSessionId(id);
  };

  return (
    <main className="min-h-screen bg-[#0c0c1a] px-4 py-10">
      {!sessionId ? <TopicInput onStart={handleStart} /> : <TurnExchange sessionId={sessionId} />}
    </main>
  );
}
