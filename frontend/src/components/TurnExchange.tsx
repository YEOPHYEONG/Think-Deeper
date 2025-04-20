// src/components/TurnExchange.tsx

"use client";

import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { sendMessage } from "@/lib/api";

export function TurnExchange({ sessionId }: { sessionId: string }) {
  const [input, setInput] = useState("");
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      const result = await sendMessage(sessionId, input);
      setResponse(result);
      setInput("");
    } catch (e) {
      setResponse("❌ 응답 오류: 백엔드 연결 확인");
    }
    setLoading(false);
  };

  return (
    <div className="w-full max-w-3xl mx-auto mt-10 space-y-6">
      <Textarea
        placeholder="당신의 생각을 입력하세요..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        className="bg-slate-900 text-slate-100 min-h-[100px]"
      />
      <Button onClick={handleSend} disabled={loading} className="w-full bg-indigo-600 hover:bg-indigo-700">
        {loading ? "전송 중..." : "Critic에게 보내기"}
      </Button>
      {response && (
        <div className="bg-gradient-to-b from-slate-800 to-slate-900 text-indigo-100 p-6 rounded-xl shadow-md whitespace-pre-wrap">
          {response}
        </div>
      )}
    </div>
  );
}
