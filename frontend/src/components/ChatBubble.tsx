// src/components/ChatBubble.tsx

import React from "react";
import ReactMarkdown from "react-markdown";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export type ChatRole = "user" | "assistant";

interface ChatBubbleProps {
  role: ChatRole;
  content: string;
}

export function ChatBubble({ role, content }: ChatBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-2`}>
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
  );
}
