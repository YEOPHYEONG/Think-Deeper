"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStore } from "./store";
import type { ChatMessage } from "./types";

interface Props {
  agentId: string;
}

export default function ChatScreen({ agentId }: Props) {
  /** Zustand 전역 상태 */
  const messages = useChatStore((s) => s.messages);
  const addUser = useChatStore((s) => s.addUser);
  const addAssistant = useChatStore((s) => s.addAssistant);

  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  /** 새 메시지마다 스크롤 아래로 */
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /** 더미 토큰 스트리머 */
  const mockStreamer = async (id: string, prompt: string) => {
    const reply = `Echo: ${prompt}`;
    for (const tok of reply.split("")) {
      await new Promise((r) => setTimeout(r, 40));
      useChatStore.getState().appendToken(id, tok);
    }
    useChatStore.getState().finishAssistant(id);
  };

  const send = async () => {
    const text = input.trim();
    if (!text) return;

    const userId = addUser(text);        // 사용자 메시지
    const asstId = addAssistant();       // 빈 assistant 메시지
    setInput("");

    mockStreamer(asstId, text);          // 토큰 단위 스트림
  };

  return (
    <div className="flex flex-col h-full w-full max-w-2xl mx-auto">
      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto space-y-2 p-4 bg-surface">
        {messages.map((m: ChatMessage) => (
          <div
            key={m.id}
            className={`p-2 rounded-lg max-w-[80%] ${
              m.role === "user"
                ? "ml-auto bg-primary text-white"
                : "mr-auto bg-slate-700"
            }`}
          >
            {m.content}
            {m.isStreaming && <span className="animate-pulse">▍</span>}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* 입력창 */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="flex gap-2 p-4 bg-[#0c0c1a]"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 px-3 py-2 rounded-md bg-surface-hover outline-none"
          placeholder="메시지를 입력하세요…"
        />
        <button
          type="submit"
          className="px-4 rounded-md bg-primary text-white disabled:opacity-40"
          disabled={!input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}
