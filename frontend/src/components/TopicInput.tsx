// src/components/TopicInput.tsx

"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

// --- onStart 타입 수정: agentType 추가 ---
export function TopicInput({ onStart }: { onStart: (topic: string, agentType: string) => void }) {
  const [topic, setTopic] = useState("");

  // --- 에이전트 선택 시 호출될 함수 ---
  const handleAgentStart = (agentType: string) => {
    if (topic.trim()) {
      onStart(topic, agentType); // 선택된 에이전트 타입 전달
    }
  }

  return (
    <div className="w-full max-w-xl mx-auto space-y-4">
      <h1 className="text-3xl text-slate-100 font-bold text-center">🧠 Think Deeper</h1>
      <p className="text-slate-400 text-center">주제를 입력하면, 선택한 AI 파트너와 사고를 시작합니다.</p>
      {/* --- Input은 그대로 유지 --- */}
       <Input
         placeholder="예: 기술 발전은 인간을 자유롭게 하는가?"
         value={topic}
         onChange={(e) => setTopic(e.target.value)}
         // Enter 키 입력 시 기본 에이전트(예: critic)로 시작하도록 할 수 있음 (선택 사항)
         onKeyDown={(e) => {
           if (e.key === "Enter" && topic.trim()) {
             handleAgentStart("critic"); // 예: Enter는 Critic으로 시작
           }
         }}
         className="bg-slate-900 text-slate-200"
       />
       {/* --- 에이전트 선택 버튼 추가 --- */}
       <div className="flex flex-wrap gap-2 justify-center pt-4">
         <Button onClick={() => handleAgentStart("critic")} disabled={!topic.trim()} className="bg-red-700 hover:bg-red-800 text-white">
           🧐 Critic과 시작
         </Button>
         <Button onClick={() => handleAgentStart("advocate")} disabled={!topic.trim()} className="bg-green-700 hover:bg-green-800 text-white">
           🤝 Advocate와 시작
         </Button>
         <Button onClick={() => handleAgentStart("why")} disabled={!topic.trim()} className="bg-blue-700 hover:bg-blue-800 text-white">
           ❓ Why와 시작
         </Button>
         <Button onClick={() => handleAgentStart("socratic")} disabled={!topic.trim()} className="bg-purple-700 hover:bg-purple-800 text-white">
           🤔 Socratic과 시작
         </Button>
         {/* 필요시 Sidekick 버튼 추가 */}
       </div>
    </div>
  );
}