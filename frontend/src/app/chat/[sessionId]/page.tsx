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
  // params promise 해제
  const { sessionId } = use(params);
  const topic = useSearchParams().get("topic") || "";

  return (
    <div className="flex-1 flex flex-col w-full max-w-3xl mx-auto h-full">
      {/* 토론 주제(있을 때만) */}
      {topic && (
        <div className="px-4 py-2 bg-slate-800 text-slate-200 border-b border-slate-700 rounded-t-3xl">
          <span className="font-semibold">토론 주제:</span>{" "}
          <span className="text-indigo-400">{topic}</span>
        </div>
      )}

      {/* 채팅창(헤더 아래 딱 붙음, 둥근 하단) */}
      <div className="flex-1 flex flex-col bg-slate-900 rounded-b-3xl overflow-hidden">
        <TurnExchange sessionId={sessionId} />
      </div>
    </div>
  );
}
