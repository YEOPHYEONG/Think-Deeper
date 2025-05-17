// src/components/TurnExchange.tsx

"use client";

import { useEffect, useRef, useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { useCallback } from "react";
import Particles from "@tsparticles/react";
import { loadSlim } from "@tsparticles/slim";
import type { Engine } from "@tsparticles/engine";
import {
  sendMessage,
  fetchSessionMessages,
  Message,
  ApiError,
} from "@/lib/api";
import { ChatBubble, ChatRole } from "./ChatBubble";
import { PaperAirplaneIcon } from "@heroicons/react/24/solid";
import { ArrowPathIcon } from "@heroicons/react/24/outline";

// 사이드킥 컴포넌트 분리
function Sidekick() {
  return (
    <motion.div 
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ delay: 0.2 }}
      className="flex flex-col h-full w-full rounded-2xl shadow-xl border border-indigo-500/30 overflow-hidden"
      style={{ backgroundColor: '#0c0c1a00' }}
    >
      {/* 게임스러운 배경 효과 */}
      {/* <div className="absolute inset-0 bg-gradient-to-b from-indigo-500/10 to-purple-500/10 pointer-events-none" /> */}
      <div className="p-4 border-b border-slate-700 relative z-10">
        <h3 className="text-base font-semibold text-white">사이드킥</h3>
        <p className="text-sm text-slate-200 font-medium mt-1">웹 검색 결과가 여기에 표시됩니다</p>
      </div>
      <div className="flex-1 overflow-y-auto p-4 relative z-10 flex flex-col items-center justify-center text-center">
        {/* 검색 결과 없을 때 예시/가이드 */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="flex flex-col items-center justify-center gap-2 text-base text-slate-200 font-medium"
        >
          <span className="text-4xl">🔎</span>
          <span>검색 결과가 없습니다.<br />메시지에 검색이 필요한 내용을 포함해보세요.<br /><span className='text-slate-400 text-sm'>(예: "최신 통계 찾아줘", "관련 뉴스 알려줘" 등)</span></span>
        </motion.div>
      </div>
    </motion.div>
  );
}

export function TurnExchange({ sessionId, agentType }: { sessionId: string, agentType: string }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [showParticles, setShowParticles] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // 파티클 초기화
  const particlesInit = useCallback(async (engine: Engine) => {
    await loadSlim(engine);
  }, []);

  // 1) 세션 히스토리 로드
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const history = await fetchSessionMessages(sessionId);
        if (history.length === 0) {
          setMessages([
            { role: "assistant", content: "안녕하세요! Deep Thinker에 오신 것을 환영합니다. 토론을 시작할 주제를 알려주세요." }
          ]);
        } else {
          setMessages(history);
        }
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

  // 2) 새 메시지마다 스크롤 아래로
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 3) 메시지 전송
  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;

    setLoading(true);
    setInput("");
    setShowParticles(true);
    setTimeout(() => setShowParticles(false), 1000);

    // 사용자 메시지를 먼저 추가
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    try {
      const response = await sendMessage(sessionId, text);
      setMessages((prev) => [...prev, response]);
    } catch (e) {
      console.error("메시지 전송 실패", e);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "❌ 메시지 전송 실패" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex md:flex-row flex-col h-full w-full gap-6 items-stretch">
      {/* 메인 채팅 영역 */}
      <div className="md:flex-[8] flex-1 flex flex-col relative min-w-0 rounded-2xl shadow-2xl border border-indigo-500/30 overflow-hidden" style={{ backgroundColor: '#0c0c1a00' }}>
        {/* 그리드 배경 */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
        {/* 파티클 효과 */}
        {showParticles && (
          <Particles
            id="tsparticles"
            init={particlesInit}
            options={{
              fullScreen: false,
              particles: {
                number: { value: 50 },
                color: { value: "#818cf8" },
                shape: { type: "circle" },
                opacity: { value: 0.5 },
                size: { value: 3 },
                move: {
                  enable: true,
                  speed: 2,
                  direction: "top",
                  outModes: "out",
                },
              },
              duration: 1,
            }}
            className="absolute inset-0 pointer-events-none"
          />
        )}
        <div className="flex-1 overflow-y-auto px-2 md:px-4 py-4 md:py-6 space-y-4 pb-28 md:pb-36 relative z-10 scrollbar-thin scrollbar-thumb-indigo-700/60 scrollbar-track-transparent">
          <AnimatePresence>
            {messages.map((msg, idx) => (
              <ChatBubble key={idx} role={msg.role as ChatRole} content={msg.content} agentType={agentType} />
            ))}
          </AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <ChatBubble role="assistant" content="답변 작성 중..." agentType={agentType} />
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>
        <motion.div 
          className="absolute bottom-2 md:bottom-4 left-0 right-0 px-2 md:px-4 z-20"
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ type: "spring", stiffness: 100 }}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2 bg-slate-800/90 border-2 border-indigo-500/50 rounded-2xl p-2 md:p-4 shadow-xl hover:shadow-2xl transition-all relative overflow-hidden"
          >
            {/* 게임스러운 테두리 효과 */}
            {/* <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 animate-pulse" /> */}
            <Textarea
              placeholder="당신의 생각을 입력하세요... (Enter로 전송)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              className="flex-1 resize-none bg-slate-800/90 text-white font-medium min-h-[44px] md:min-h-[48px] max-h-[200px] rounded-xl border-2 border-indigo-500/50 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-400/40 focus:shadow-lg transition-all backdrop-blur-sm placeholder:text-slate-400 placeholder:text-base placeholder:text-left py-2 md:py-3 hover:bg-slate-800/80"
            />
            <Button
              type="submit"
              aria-label="메시지 전송"
              disabled={loading}
              className="h-[44px] w-[44px] md:h-[48px] md:w-[48px] min-w-[44px] min-h-[44px] md:min-w-[48px] md:min-h-[48px] p-0 bg-indigo-600 hover:bg-indigo-700 rounded-full transition-all transform hover:scale-110 active:scale-95 flex items-center justify-center relative overflow-hidden text-white focus:ring-2 focus:ring-indigo-400/40 focus:ring-offset-2"
            >
              {loading ? (
                <ArrowPathIcon className="w-6 h-6 animate-spin" />
              ) : (
                <PaperAirplaneIcon className="w-6 h-6 rotate-45" />
              )}
            </Button>
          </form>
        </motion.div>
      </div>
      {/* 사이드킥 영역 */}
      <div className="md:flex-[2] flex-1 flex flex-col min-w-[0] max-w-full md:min-w-[280px] md:max-w-[400px] h-full mt-4 md:mt-0">
        <Sidekick />
      </div>
    </div>
  );
}
