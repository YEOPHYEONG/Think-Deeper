// src/features/select/SelectScreen.tsx
"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import { useRouter } from "next/navigation";

import { useCharacters } from "./lib/useCharacters";
import BackgroundImage from "@/features/select/components/BackgroundImage";
import CharacterGrid from "@/features/select/components/CharacterGrid";
import InfoPanel from "@/features/select/components/InfoPanel";
import BGMManager from "@/features/select/components/BGMManager";
import SoundToggle from "./components/SoundToggle";
import { playSFX } from "./components/SFXManager";
import TransitionOverlay from "@/features/select/components/TransitionOverlay";

import { useAgentStore } from "@/lib/store/agentStore";
import { useSelectStore } from "@/features/select/store";
import { useSelectInput } from "@/features/select/hooks/useSelectInput";
import { createSession } from "@/lib/api";

const MIN_READY = 1;

export default function SelectScreen() {
  /* 초기화 */
  useEffect(() => {
    const { clearReady, setShowOverlay } = useAgentStore.getState();
    clearReady();
    setShowOverlay(false);
  }, []);

  /* 스토어, 훅 */
  const roster     = useCharacters();
  const readyCount = useAgentStore(s => s.readyIds.length);
  const setShowOv  = useAgentStore(s => s.setShowOverlay);
  const cursor     = useSelectStore(s => s.cursor);
  useSelectInput(roster);

  /* 인트로 페이드 */
  const [showIntro, setShowIntro]   = useState(true);
  const [introDone, setIntroDone]   = useState(false);
  useEffect(() => {
    const t1 = setTimeout(() => setShowIntro(false), 1500);
    const t2 = setTimeout(() => setIntroDone(true), 1600);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  /* Next 클릭 */
  const router = useRouter();
  const handleNext = async () => {
    if (readyCount < MIN_READY) return;
    setShowOv(true);
    playSFX("confirm");
    const ids = useAgentStore.getState().readyIds;

    setTimeout(async () => {
      if (ids.length === 1) {
        const agentId = ids[0];
        const meta = roster.find(c => c.id === agentId);
        const topic = meta ? `${meta.name} 세션` : "토론 세션";

        try {
          const sessionId = await createSession(topic, agentId);
          router.push(`/chat/${sessionId}?topic=${encodeURIComponent(topic)}&agent=${agentId}`);
        } catch (e) {
          alert("세션 생성 실패: " + (e instanceof Error ? e.message : e));
        }
      } else {
        router.push(`/chat/multi?agents=${ids.join(",")}`);
      }
    }, 1800);
  };

  return (
    <main className="relative h-screen overflow-hidden bg-[#0c0c1a] text-white">
      {/* 배경 비디오 + 선택 캐릭터 배경 */}
      <motion.video
        className="absolute inset-0 w-full h-full object-cover z-0 filter blur-md brightness-50"
        src="/videos/bg.mp4"
        autoPlay loop muted playsInline
        initial={showIntro ? { scale: 1, opacity: 1 } : undefined}
        animate={showIntro ? { scale: 2, opacity: 0 } : { scale: 1, opacity: 1 }}
        transition={{ duration: 2, ease: "easeInOut" }}
      />
      <BackgroundImage introDone={introDone} />

      {/* 오버레이 */}
      <AnimatePresence>
        {introDone && (
          <motion.div
            className="fixed inset-0 bg-black/50 z-10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          />
        )}
      </AnimatePresence>

      {/* 메인 UI */}
      <AnimatePresence>
        {introDone && (
          <motion.div
            className="relative z-20 flex flex-col items-center justify-center h-full gap-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.2 }}
          >
            {/* 상단 컨트롤 */}
            <div className="absolute top-4 right-4 flex space-x-2">
              <SoundToggle />
              <BGMManager />
            </div>

            {/* 제목 */}
            <h1 className="text-3xl font-extrabold">
              🚀 Deep Thinker: 에이전트 선택
            </h1>

            {/* 캐릭터 그리드 + InfoPanel 묶음 */}
            <div className="flex justify-center items-center gap-8 px-6 w-full">
              <div className="flex justify-center items-center gap-8 max-w-[90vw] mx-auto w-full">
                <div className="w-full flex-shrink">
                  <CharacterGrid roster={roster} />
                </div>

                {cursor !== null && roster[cursor] && (
                  <div className="ml-12 flex-shrink-0 w-[340px] h-[360px] flex flex-col justify-center">
                    <InfoPanel meta={roster[cursor]} />
                  </div>
                )}
              </div>
            </div>

            {/* Next 버튼 */}
            <div className="mt-6 flex justify-center">
              <button
                onClick={handleNext}
                disabled={readyCount < MIN_READY}
                className={clsx(
                  "px-8 py-3 rounded-lg font-semibold transition-colors duration-150",
                  "border-2 border-white/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-white",
                  readyCount >= MIN_READY
                    ? "bg-primary text-white hover:bg-primary/90"
                    : "bg-surface text-slate-400 opacity-40 cursor-not-allowed"
                )}
              >
                NEXT
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 클릭 시 잉크 스플래시 */}
      <TransitionOverlay />
    </main>
  );
}
