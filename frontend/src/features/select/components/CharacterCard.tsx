"use client";

// CharacterCard.tsx 맨 위에 추가
import { playSFX } from "./SFXManager";
import clsx from "clsx";
import { motion, type Variants } from "framer-motion";
import { useAgentStore }  from "@/lib/store/agentStore";
import { useSelectStore } from "@/features/select/store";
import type { CharacterMeta } from "../types";


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
    playSFX("click")
    const { toggleReady } = useAgentStore.getState();
    const { setCursor }   = useSelectStore.getState();
    setCursor(index);
    toggleReady(c.id);
  };

  return (
    <motion.button
      onMouseEnter={() => {
        setCursor(index);
        playSFX("hover")}}
      onClick={handleClick}
      variants={variants}
      animate={current}
      className={clsx(
        "relative w-40 h-48 rounded-md overflow-hidden border-4 transition-all duration-150 focus:outline-none",
        !isFocused && !isReadySel && "border-[#334155]"
      )}
      style={{ borderColor: isFocused || isReadySel ? color : undefined }}
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
          className="absolute inset-0 bg-white/80 flex items-center justify-center text-3xl font-extrabold text-black"
        >
          READY
        </motion.div>
      )}

      {/* 순서 배지 */}
      {isReadySel && (
        <span
          className="absolute top-0 left-0 text-[10px] text-white px-1 rounded-br"
          style={{ backgroundColor: color }}
        >
          P{order + 1}
        </span>
      )}

      {/* 역할 라벨 */}
      <span
        className="absolute bottom-1 left-1 right-1 text-center text-xs rounded-md backdrop-blur-sm font-semibold text-white"
        style={{
          backgroundColor: isReadySel ? color : "rgba(0,0,0,0.6)",
        }}
      >
        {c.role}
      </span>
    </motion.button>
  );
}
