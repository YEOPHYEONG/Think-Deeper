"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { Suspense } from "react";

/* 임시: 에이전트 메타 데이터 */
const AGENT_META: Record<string, { name: string; role: string }> = {
  critic:    { name: "Critic",    role: "비판자" },
  mediator:  { name: "Mediator",  role: "중재자" },
  searcher:  { name: "Searcher",  role: "탐색자" },
  advocate:  { name: "Advocate",  role: "옹호자" },
  // … 필요 시 추가
};

export default function MultiChatPage() {
  const params  = useSearchParams();
  const router = useRouter();
  const agents  = params.get("agents")?.split(",").filter(Boolean) || [];

  return (
    <main className="flex flex-col h-screen text-white bg-[#0d0d17]">
       {/* ───── 네비게이션 바 ───── */}
      <div className="flex justify-between items-center p-4 bg-[#0d0d17]">
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
      {/* 상단 에이전트 리스트 */}
      <header className="p-4 flex gap-4 border-b border-white/10">
        {agents.map((id) => (
          <div key={id} className="px-3 py-1 bg-primary/80 rounded-lg text-sm">
            {AGENT_META[id]?.name ?? id}
          </div>
        ))}
      </header>

      {/* 대화 영역 */}
      <section className="flex-1 overflow-y-auto p-6 space-y-4">
        <Suspense fallback={<p>Loading conversation...</p>}>
          {/* TODO: 멀티 에이전트 대화 스트림 컴포넌트 */}
          <p className="text-center text-gray-400">
            🚧 멀티 에이전트 대화 엔진 연결 예정
          </p>
        </Suspense>
      </section>

      {/* 사용자 입력 */}
      <footer className="p-4 border-t border-white/10">
        <input
          type="text"
          placeholder="토론 주제를 입력하세요…"
          className="w-full bg-[#1a1a29] p-3 rounded-md outline-none"
        />
      </footer>
    </main>
  );
}
