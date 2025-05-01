// src/components/ChatBubble.tsx

import React from "react";
import ReactMarkdown from "react-markdown";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import CriticOutput from "./CriticOutput"; // 새로 만든 컴포넌트

export type ChatRole = "user" | "assistant";

interface ChatBubbleProps {
  role: ChatRole;
  content: string;
  lastCriticOutput?: {
    critique_point: string;
    brief_elaboration: string;
    request_search_query?: string | null;
  };
}

export function ChatBubble({ role, content, lastCriticOutput }: ChatBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} mb-4`}>
      <div className="flex items-start">
        {!isUser && (
          <Avatar className="mr-2">
            <AvatarFallback>🤖</AvatarFallback>
          </Avatar>
        )}
        <div
          className={`max-w-[70%] p-4 rounded-2xl whitespace-pre-wrap prose prose-invert text-sm
            ${isUser ? "bg-indigo-600 text-white rounded-br-none" : "bg-slate-800 text-slate-200 rounded-bl-none"}`}
        >
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
        {isUser && (
          <Avatar className="ml-2">
            <AvatarFallback>👤</AvatarFallback>
          </Avatar>
        )}
      </div>

      {/* 🎯 Critic 분석 결과가 있을 경우 렌더링 */}
      {!isUser && lastCriticOutput && (
        <CriticOutput
          critiquePoint={lastCriticOutput.critique_point}
          briefElaboration={lastCriticOutput.brief_elaboration}
          requestSearchQuery={lastCriticOutput.request_search_query}
        />
      )}
    </div>
  );
}
