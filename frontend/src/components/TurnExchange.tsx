// src/components/TurnExchange.tsx

"use client";

import { useEffect, useRef, useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  sendMessage,
  fetchSessionMessages,
  Message,
  ApiError,
} from "@/lib/api";
import { ChatBubble, ChatRole } from "./ChatBubble";

export function TurnExchange({ sessionId }: { sessionId: string }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // 1) 세션 히스토리 로드
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const history = await fetchSessionMessages(sessionId);
        setMessages(history);
      } catch (e) {
        console.error("초기 메시지 불러오기 실패", e);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "❌ 히스토리 로드 실패" },
        ]);
      }
    };
    loadHistory();
  }, [sessionId]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setInput("");

    try {
      const assistantMsg = await sendMessage(sessionId, input);
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        // HTTP 상태별 분기 가능
        if (e.status === 401) {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: "❌ 세션이 만료되었습니다. 새로고침 후 다시 시도해주세요.",
            },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `❌ 서버 오류(${e.status}): ${e.message}`,
            },
          ]);
        }
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "❌ 네트워크 오류 발생" },
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  // 스크롤 맨 아래로
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="relative flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 pb-36">
        {messages.map((msg, idx) => (
          <ChatBubble key={idx} role={msg.role as ChatRole} content={msg.content} />
        ))}
        {loading && <ChatBubble role="assistant" content="답변 작성 중..." />}
        <div ref={bottomRef} />
      </div>

      <div className="absolute bottom-4 left-0 right-0 px-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-end gap-2 bg-[#0c0c1a] border border-slate-700 rounded-2xl p-4 shadow-xl"
        >
          <Textarea
            placeholder="당신의 생각을 입력하세요..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            className="flex-1 resize-none bg-slate-800 text-slate-100 min-h-[48px] max-h-[200px] rounded-xl"
          />
          <Button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-700 rounded-xl"
          >
            {loading ? "전송 중..." : "전송"}
          </Button>
        </form>
      </div>
    </div>
  );
}
