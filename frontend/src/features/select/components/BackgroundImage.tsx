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
        let style: React.CSSProperties;
        if (count === 2) {
          style = {
            width: "50%",
            left: `${50 * idx}%`,
            zIndex: idx,
            opacity: 0.9,
          };
        } else if (count === 1) {
          style = {
            width: "100%",
            left: 0,
            zIndex: idx,
            opacity: 0.9,
          };
        } else {
          const leftOffset = sliceWidth * idx;
          style = {
            width: `${sliceWidth}%`,
            left: `${leftOffset}%`,
            zIndex: idx,
            opacity: 0.9,
          };
        }
        return (
          <motion.img
            key={c.id}
            src={`/img/backgrounds/${c.id}.png`}
            className={`absolute top-0 h-full pointer-events-none bg-black/50 ${count === 1 ? "object-contain" : "object-cover"}`}
            style={style}
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
