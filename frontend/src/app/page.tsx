// src/app/page.tsx

"use client";

import { useRouter } from "next/navigation";
import { createSession } from "@/lib/api";
import { TopicInput } from "@/components/TopicInput";

export default function Home() {
  const router = useRouter();

  const handleStart = async (topic: string) => {
    const id = await createSession(topic);
    router.push(`/chat/${id}?topic=${encodeURIComponent(topic)}`);
  };

  return (
    <main className="min-h-screen bg-[#0c0c1a] px-4 py-10">
      <TopicInput onStart={handleStart} />
    </main>
  );
}
