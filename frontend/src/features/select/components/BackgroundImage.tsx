"use client";

import { useAgentStore } from "@/lib/store/agentStore";
import { useCharacters } from "@/features/select/lib/useCharacters";
import { motion, AnimatePresence } from "framer-motion";

export default function BackgroundImage({ introDone }: { introDone: boolean }) {
  const readyIds = useAgentStore((s) => s.readyIds);
  const roster = useCharacters();

  if (!introDone || readyIds.length === 0) return null;

  const selected = readyIds
    .map((id) => roster.find((r) => r.id === id))
    .filter(Boolean) as { id: string }[];

  const count = selected.length;
  const sliceWidth = 100 / count; // 분할 너비(%)

  return (
    <AnimatePresence>
      {selected.map((c, idx) => {
        const leftOffset = sliceWidth * idx; // 각 이미지의 왼쪽 위치(%)
        return (
          <motion.img
            key={c.id}
            src={`/img/backgrounds/${c.id}.png`}
            className="absolute top-0 h-full object-contain pointer-events-none bg-black/50"
            style={{
              // 너비를 전체 나눈 만큼 지정, 좌측 오프셋도 %
              width: `${sliceWidth}%`,
              left: `${leftOffset}%`,
              zIndex: idx,
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.9 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          />
        );
      })}

      {/* (선택) 아주 은은한 오버레이가 필요하면 활성화하세요 */}
      {/* <motion.div
        className="absolute inset-0 z-50 bg-black/10 mix-blend-multiply pointer-events-none"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.5 }}
      /> */}
    </AnimatePresence>
  );
}
