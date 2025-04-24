// src/app/chat/[sessionId]/page.tsx

"use client";

import { use } from "react";
import { useSearchParams } from "next/navigation";
import { TurnExchange } from "@/components/TurnExchange";

export default function ChatPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = use(params);
  const topic = useSearchParams().get("topic") || "";

  return (
    <main className="min-h-screen w-full bg-[#0c0c1a] flex justify-center">
      <div className="w-full max-w-3xl h-screen flex flex-col">
        {/* 상단 고정: 토론 주제 */}
        <header className="sticky top-0 z-10 bg-slate-800 text-slate-200 px-4 py-3 border-b border-slate-700">
          <span className="font-semibold">토론 주제:</span>{" "}
          <span className="text-indigo-400">{topic}</span>
        </header>

        {/* 메시지 + 입력창 */}
        <div className="flex-1 flex flex-col overflow-hidden bg-slate-900">
          <TurnExchange sessionId={sessionId} />
        </div>
      </div>
    </main>
  );
}
