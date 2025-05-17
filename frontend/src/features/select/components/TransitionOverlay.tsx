// src/features/select/components/TransitionOverlay.tsx
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useAgentStore } from "@/lib/store/agentStore";
import { useCharacters } from "@/features/select/lib/useCharacters";

export default function TransitionOverlay() {
  const showOv = useAgentStore((s) => s.showOverlay);
  const readyIds = useAgentStore((s) => s.readyIds);
  const roster = useCharacters();

  const userCharacter = {
    id: "user",
    name: "USER",
    role: "플레이어",
    portrait: "/img/roster/user.png",
    vsPortrait: "/img/roster/user.png",
  };

  const left = roster.find((c) => c.id === readyIds[0]);
  const right = roster.find((c) => c.id === readyIds[1]) || userCharacter;

  // ✅ 라우팅 제거: router.push() 없이 전환 효과만 유지
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
            src={left.vsPortrait || left.portrait}
            alt={left.name}
            className="absolute left-0 top-1/2 -translate-y-1/2 ml-16 h-[600px] z-50 object-contain drop-shadow-xl"
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        )}

        {/* 👤 우측 캐릭터 */}
        {right && (
          <motion.img
            src={right.vsPortrait || right.portrait}
            alt={right.name}
            className="absolute right-0 top-1/2 -translate-y-1/2 mr-16 h-[600px] z-50 object-contain drop-shadow-xl scale-x-[-1]"
            initial={{ x: 300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        )}
      </motion.div>
    </AnimatePresence>
  );
}
