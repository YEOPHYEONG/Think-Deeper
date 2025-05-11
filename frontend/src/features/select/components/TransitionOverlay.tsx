// src/features/select/components/TransitionOverlay.tsx
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAgentStore } from "@/lib/store/agentStore";
import { useCharacters } from "@/features/select/lib/useCharacters";
export default function TransitionOverlay() {
  const showOv = useAgentStore((s) => s.showOverlay);
  const readyIds = useAgentStore((s) => s.readyIds);
  const roster = useCharacters();
  const router = useRouter(); // ✅ 이 줄 추가!

  const left = roster.find((c) => c.id === readyIds[0]);
  const right = roster.find((c) => c.id === readyIds[1]);

  useEffect(() => {
    if (!showOv) return;

    const timer = setTimeout(() => {
      if (readyIds.length === 1) {
        router.push(`/chat/agent?agent=${readyIds[0]}`);
      } else {
        router.push(`/chat/multi?agents=${readyIds.join(",")}`);
      }
    }, 2200); // ⏳ 2.2초 후 라우팅

    return () => clearTimeout(timer);
  }, [showOv]);

  if (!showOv) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 bg-black overflow-hidden"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* 🔥 불꽃 효과 */}
        <motion.img
          src="/img/effect/flame_overlay.png"
          alt="flame"
          className="absolute inset-0 w-full h-full object-cover mix-blend-screen opacity-90 pointer-events-none"
          initial={{ scale: 1.2, opacity: 0 }}
          animate={{ scale: 1, opacity: 0.9 }}
          transition={{ duration: 0.6 }}
        />

        {/* 👤 좌측 캐릭터 */}
        {left && (
          <motion.img
            src={left.portrait}
            alt={left.name}
            className="absolute left-12 bottom-20 h-[380px] z-50 object-contain drop-shadow-xl"
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        )}

        {/* 👤 우측 캐릭터 */}
        {right && (
          <motion.img
            src={right.portrait}
            alt={right.name}
            className="absolute right-12 bottom-20 h-[380px] z-50 object-contain drop-shadow-xl scale-x-[-1]"
            initial={{ x: 300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        )}
      </motion.div>
    </AnimatePresence>
  );
}
