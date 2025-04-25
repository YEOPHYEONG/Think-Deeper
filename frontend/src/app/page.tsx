// src/app/page.tsx

"use client";

import { useRouter } from "next/navigation";
import { createSession } from "@/lib/api";
import { TopicInput } from "@/components/TopicInput";
import { useState } from "react"; // 로딩 상태 추가

export default function Home() {
  const router = useRouter();
  const [loading, setLoading] = useState(false); // 로딩 상태 추가
  const [error, setError] = useState<string | null>(null); // 에러 상태 추가

  // --- handleStart 시그니처 변경 ---
  const handleStart = async (topic: string, agentType: string) => {
    setLoading(true); // 로딩 시작
    setError(null); // 이전 에러 초기화
    try {
      // --- createSession 호출 시 agentType 전달 ---
      const id = await createSession(topic, agentType);
      // --- URL에 agentType 포함하여 리디렉션 ---
      router.push(`/chat/${id}?topic=${encodeURIComponent(topic)}&agent=${agentType}`);
    } catch (e: unknown) {
       console.error("세션 생성 실패:", e);
       setError(e instanceof Error ? e.message : "세션 생성 중 오류 발생"); // 에러 메시지 설정
       setLoading(false); // 로딩 종료 (에러 시)
    }
    // 성공 시 페이지 이동하므로 setLoading(false) 필요 없음
  };

  return (
    <main className="min-h-screen bg-[#0c0c1a] px-4 py-10 flex items-center justify-center">
      <div className="w-full max-w-xl">
        <TopicInput onStart={handleStart} />
        {/* --- 로딩 및 에러 표시 추가 --- */}
        {loading && <p className="text-center text-slate-400 mt-4">세션 생성 중...</p>}
        {error && <p className="text-center text-red-500 mt-4">오류: {error}</p>}
      </div>
    </main>
  );
}