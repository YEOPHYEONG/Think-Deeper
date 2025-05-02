// src/app/chat/[sessionId]/page.tsx

"use client";

import { use } from "react";
import { useSearchParams } from "next/navigation";
import { TurnExchange } from "@/components/TurnExchange";

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
    <div className="flex flex-col w-full max-w-3xl mx-auto h-screen"> {/* 화면 전체 높이 사용 */}
      {/* --- 헤더 영역: 주제 및 현재 에이전트 표시 --- */}
      {(topic || agentType !== 'default') && ( // 주제 또는 기본 에이전트가 아닐 때 헤더 표시
        <div className="px-4 py-3 bg-slate-800 text-slate-300 border-b border-slate-700 rounded-t-xl flex justify-between items-center flex-shrink-0"> {/* 높이 고정 */}
          <div className="text-sm truncate pr-2"> {/* 주제가 길 경우 잘림 처리 */}
             <span className="font-semibold text-slate-100">토론 주제:</span>{" "}
             <span className="text-indigo-400">{topic || "없음"}</span>
          </div>
          <div className="text-sm font-medium bg-slate-700 px-2 py-1 rounded">
            {/* 이모지와 이름 표시 */}
            {agentInfo.emoji} {agentInfo.name}
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