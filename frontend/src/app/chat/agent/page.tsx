"use client";                            // ⬅️ Server 기능 없으면 이렇게 간단

import PageFade from "@/components/PageFade";
import ChatScreen from "@/features/chat/ChatScreen";
import data from "@/features/select/data/characters.json" assert { type: "json" };
import type { CharacterMeta } from "@/features/select/types";
import { useRouter, useSearchParams } from "next/navigation";

export default function AgentPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const id = searchParams.get("agent") ?? "";
  const character = (data as CharacterMeta[]).find((c) => c.id === id) ?? {
    id: "unknown",
    name: "Unknown",
    role: "Unknown",
    portrait: "",
    country: "KR",
  };

  return (
    <PageFade>
      {/* ───── 네비게이션 바 ───── */}
      <div className="flex justify-between items-center p-4">
        <button
          onClick={() => router.back()}
          className="px-3 py-1 bg-white text-black rounded hover:opacity-80"
        >
          ← 뒤로가기
        </button>
        <button
          onClick={() => router.push("/select")}
          className="px-3 py-1 bg-white text-black rounded hover:opacity-80"
        >
          🏠 메인으로
        </button>
      </div>
      <header className="flex flex-col items-center py-6 gap-3">
        <img
          src={character.portrait}
          alt={character.name}
          className="w-32 h-32 rounded-full border-4 border-primary"
        />
        <h1 className="text-2xl font-bold">
          {character.role} {character.name}
        </h1>
      </header>

      <section className="flex-1 min-h-0">
        <ChatScreen agentId={character.id} />
      </section>
    </PageFade>
  );
}
