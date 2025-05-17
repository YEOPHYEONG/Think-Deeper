// src/app/chat/[sessionId]/page.tsx

"use client";

import { use } from "react";
import { useSearchParams } from "next/navigation";
import { TurnExchange } from "@/components/TurnExchange";
import Link from "next/link";

// --- 에이전트 타입별 표시 이름 및 이모지 매핑 ---
const AGENT_DISPLAY_INFO: { [key: string]: { name: string; emoji: string } } = {
  critic: { name: "Critic", emoji: "🧐" },
  advocate: { name: "Advocate", emoji: "🤝" },
  why: { name: "Why", emoji: "❓" },
  socratic: { name: "Socratic", emoji: "🤔" },
  // 필요시 다른 에이전트 추가
  default: { name: "Assistant", emoji: "🤖" } // 기본값 또는 알 수 없을 때
};
// --- ---

export default function ChatPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  // params promise 해제
  const { sessionId } = use(params);
  const searchParams = useSearchParams(); // useSearchParams 훅 사용
  const topic = searchParams.get("topic") || "";
  // --- URL 쿼리에서 'agent' 파라미터 읽기 ---
  const agentType = searchParams.get("agent") || "default"; // 없으면 'default'
  // 매핑을 사용하여 표시 정보 가져오기
  const agentInfo = AGENT_DISPLAY_INFO[agentType] || AGENT_DISPLAY_INFO.default;
  // --- ---

  return (
    // --- flex-1 및 h-full 제거하여 내용만큼 높이 차지하도록 변경 가능 (선택사항) ---
    <div className="flex flex-col w-full h-screen"> {/* 화면 전체 높이와 너비 사용 */}
      {/* --- 헤더 영역: 주제 및 현재 에이전트 표시 --- */}
      {(topic || agentType !== 'default') && (
        <div className="px-6 py-4 text-slate-100 border-b-2 border-indigo-500 shadow-lg rounded-t-2xl flex justify-between items-center flex-shrink-0 gap-4" style={{ backgroundColor: '#0c0c1a00' }}>
          {/* ← 뒤로가기 버튼 */}
          <Link href="/select" className="text-2xl font-bold text-indigo-400 hover:text-indigo-300 transition-colors mr-2 flex items-center"><span className="text-3xl mr-1">←</span> </Link>
          <div className="flex-1 flex flex-col min-w-0">
            <div className="text-lg font-bold text-indigo-300 truncate">토론 주제: <span className="text-white">{topic || "없음"}</span></div>
          </div>
          <div className="flex items-center gap-2 bg-indigo-700/80 px-4 py-2 rounded-xl shadow font-bold text-lg text-white">
            <span className="text-2xl">{agentInfo.emoji}</span>
            <span>{agentInfo.name}</span>
          </div>
        </div>
      )}
      {/* --- --- */}

      {/* --- 채팅창 영역: 남은 공간 모두 차지 --- */}
      {/* 헤더가 있으면 상단 모서리 둥글게 처리 제거, 하단만 유지 */}
      <div className={`flex-1 flex flex-col bg-slate-900 overflow-hidden ${ (topic || agentType !== 'default') ? 'rounded-b-xl' : 'rounded-xl'}`}>
        <TurnExchange sessionId={sessionId} agentType={agentType} />
      </div>
      {/* --- --- */}
    </div>
  );
}