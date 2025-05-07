// src/features/select/SelectScreen.tsx
"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import { useRouter } from "next/navigation";

import { useCharacters } from "./lib/useCharacters";
import CharacterGrid from "@/features/select/components/CharacterGrid";
import InfoPanel from "@/features/select/components/InfoPanel";
import BGMManager from "@/features/select/components/BGMManager";
import SoundToggle from "./components/SoundToggle";
import { playSFX } from "./components/SFXManager";
import TransitionOverlay from "@/features/select/components/TransitionOverlay";

import { useAgentStore } from "@/lib/store/agentStore";
import { useSelectStore } from "@/features/select/store";      // cursor, setCursor
import { useSelectInput } from "@/features/select/hooks/useSelectInput";

const MIN_READY = 1; // 버튼 활성화 기준(선택 ≥ 1)

export default function SelectScreen() {
  /* ───────── 초기화 ───────── */
  useEffect(() => {
    const { clearReady, setShowOverlay } = useAgentStore.getState();
    clearReady();            // readyIds 비우기
    setShowOverlay(false);   // 오버레이 플래그 리셋
  }, []);

  /* ───────── 스토어 값 ───────── */
  const roster      = useCharacters();
  const readyCount  = useAgentStore((s) => s.readyIds.length);
  const setShowOv   = useAgentStore((s) => s.setShowOverlay);

  const cursor      = useSelectStore((s) => s.cursor);        // 현재 포커스 인덱스
  useSelectInput(roster);                                     // 키보드/패드 입력 훅

  /* ───────── 인트로 페이드 ───────── */
  const [showIntro, setShowIntro] = useState(true);
  const [introDone, setIntroDone] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setShowIntro(false), 1500);
    const t2 = setTimeout(() => setIntroDone(true), 1600);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  /* ───────── Next 클릭 ───────── */
  const router = useRouter();
  const handleNext = () => {
    if (readyCount < MIN_READY) return;

    setShowOv(true);          // 1) 오버레이 표시
    playSFX("confirm");

    const ids = useAgentStore.getState().readyIds;
    setTimeout(() => {        // 2) 1.8 초 뒤 라우팅
      if (ids.length === 1) {
        router.push(`/chat/agent?agent=${ids[0]}`);
      } else {
        router.push(`/chat/multi?agents=${ids.join(",")}`);
      }
    }, 1800);
  };

  /* ───────── 렌더 ───────── */
  return (
    <main className="relative h-screen overflow-hidden bg-[#0c0c1a] text-white">
      {/* 배경 비디오 인트로 */}
      <motion.video
        className="absolute inset-0 w-full h-full object-cover z-0 filter blur-md brightness-50"
        src="/videos/bg.mp4"
        autoPlay loop muted playsInline
        initial={showIntro ? { scale: 1, opacity: 1 } : undefined}
        animate={showIntro ? { scale: 2, opacity: 0 } : { scale: 1, opacity: 1 }}
        transition={{ duration: 2, ease: "easeInOut" }}
      />

      {/* 반투명 오버레이 */}
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
            {/* 사운드 토글 & BGM */}
            <div className="absolute top-4 right-4"><SoundToggle /></div>
            <BGMManager />

            {/* 제목 */}
            <h1 className="text-3xl font-extrabold">
              🚀 Think Deeper: 에이전트 선택
            </h1>

            {/* 캐릭터 그리드 */}
            <CharacterGrid roster={roster} />

            {/* InfoPanel : 커서가 가리키는 캐릭터 */}
            {cursor !== null && roster[cursor] && (
              <InfoPanel meta={roster[cursor]} />
            )}

            {/* Next 버튼 */}
            <button
              onClick={handleNext}
              disabled={readyCount < MIN_READY}
              className={clsx(
                "mt-6 px-10 py-3 rounded-lg font-semibold transition-colors duration-150",
                "border border-white border-opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-white",
                readyCount >= MIN_READY
                  ? "bg-primary text-white hover:bg-primary/90"
                  : "bg-surface text-slate-400 opacity-40 cursor-not-allowed"
              )}
            >
              Next
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Next 클릭 시 잉크 스플래시 */}
      <TransitionOverlay />
    </main>
  );
}
