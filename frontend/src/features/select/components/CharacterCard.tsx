"use client";

// CharacterCard.tsx 맨 위에 추가
import clsx from "clsx";
import { motion, type Variants } from "framer-motion";
import { useAgentStore }  from "@/lib/store/agentStore";
import { useSelectStore } from "@/features/select/store";
import type { CharacterMeta } from "../types";
import { useState } from "react";


/* READY 순서별 팔레트 */
const COLORS = [
  "rgb(248,113,113)",
  "rgb(96,165,250)",
  "rgb(134,239,172)",
  "rgb(249,115,22)",
] as const;

// 기본 흰색
const DEFAULT_COLOR = "#ffffff";

export default function CharacterCard({
  c,
  index,
}: {
  c: CharacterMeta;
  index: number;
}) {
  const readyIds = useAgentStore((s) => s.readyIds);
  const cursor   = useSelectStore((s) => s.cursor);
  const setCursor = useSelectStore((s) => s.setCursor);
  const [isFlipped, setIsFlipped] = useState(false);

  const order      = readyIds.indexOf(c.id);
  const isReadySel = order >= 0;
  const isFocused  = cursor === index;
  const color      = isReadySel ? COLORS[order % COLORS.length] : DEFAULT_COLOR;

  const variants: Variants = {
    idle: {
      scale: 1,
      boxShadow: "0 0 0 rgba(0,0,0,0)",
    },
    focus: {
      scale: 1.06,
      boxShadow: `0 0 12px ${color}`,
      transition: { duration: 0.12 },
    },
    selected: {
      scale: 1.06,
      boxShadow: [`0 0 16px ${color}`, `0 0 24px ${color}`],
      transition: { duration: 0.12 },
    },
  };
  const current = isReadySel ? "selected" : isFocused ? "focus" : "idle";

  const handleClick = () => {
    const { toggleReady } = useAgentStore.getState();
    const { setCursor }   = useSelectStore.getState();
    setCursor(index);
    toggleReady(c.id);
  };

  return (
    <motion.button
      onMouseEnter={() => {
        setCursor(index);
        setIsFlipped(true);
      }}
      onMouseLeave={() => {
        setIsFlipped(false);
      }}
      onClick={handleClick}
      variants={variants}
      animate={current}
      className={clsx(
        "relative w-full h-full min-h-[400px] rounded-md overflow-hidden border-4 transition-all duration-150 focus:outline-none",
        !isFocused && !isReadySel && "border-[#334155]"
      )}
      style={{ borderColor: isFocused || isReadySel ? color : undefined }}
    >
      <div
        className="relative w-full h-full transition-transform duration-500"
        style={{
          transformStyle: "preserve-3d",
          transform: isFlipped ? "rotateY(180deg)" : "none",
        }}
      >
        {/* 앞면 */}
        <div
          className="absolute inset-0 w-full h-full"
          style={{ backfaceVisibility: "hidden" }}
        >
          {/* 이미지 */}
          <img
            src={c.portrait}
            alt={c.name}
            className="absolute inset-0 w-full h-full object-cover pointer-events-none"
          />

          {/* READY 오버레이 */}
          {isReadySel && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="absolute inset-0 bg-white/80 flex items-center justify-center text-4xl font-extrabold text-black"
            >
              READY
            </motion.div>
          )}

          {/* 순서 배지 */}
          {isReadySel && (
            <span
              className="absolute top-0 left-0 text-sm text-white px-3 py-1 rounded-br"
              style={{ backgroundColor: color }}
            >
              P{order + 1}
            </span>
          )}

          {/* 역할 라벨 */}
          <span
            className="absolute bottom-3 left-3 right-3 text-center text-base rounded-md backdrop-blur-sm font-semibold text-white py-2"
            style={{
              backgroundColor: isReadySel ? color : "rgba(0,0,0,0.6)",
            }}
          >
            {c.role}
          </span>
        </div>

        {/* 뒷면 */}
        <div
          className="absolute inset-0 w-full h-full bg-gradient-to-b from-[#7c86ff]/30 to-[#0c0c1a]/50 backdrop-blur-md p-6 flex flex-col gap-4"
          style={{
            backfaceVisibility: "hidden",
            transform: "rotateY(180deg)",
          }}
        >
          <h2 className="text-2xl font-extrabold tracking-wide uppercase text-white">
            {c.name}
          </h2>
          <p className="text-sm text-white/60">
            ROLE: <span className="text-blue-400 font-bold">{c.role.toUpperCase()}</span>
          </p>
          {c.description && (
            <p className="text-sm text-white/90 leading-relaxed">
              {c.description}
            </p>
          )}
          {c.stats && (
            <div className="mt-4 space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-white/80">Power:</span>
                <div className="flex-1 h-2 bg-white/20 rounded-full">
                  <div className="h-full bg-red-500 rounded-full" style={{ width: `${c.stats.power}%` }} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-white/80">Logic:</span>
                <div className="flex-1 h-2 bg-white/20 rounded-full">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${c.stats.logic}%` }} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-white/80">Empathy:</span>
                <div className="flex-1 h-2 bg-white/20 rounded-full">
                  <div className="h-full bg-green-500 rounded-full" style={{ width: `${c.stats.empathy}%` }} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-white/80">Speed:</span>
                <div className="flex-1 h-2 bg-white/20 rounded-full">
                  <div className="h-full bg-yellow-500 rounded-full" style={{ width: `${c.stats.speed}%` }} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.button>
  );
}
