// src/features/select/components/InfoPanel.tsx
"use client";

import StatBar from "./StatBar";
import type { CharacterMeta } from "../types";

interface Props {
  meta: CharacterMeta;
}

export default function InfoPanel({ meta }: Props) {
  const { stats, name, role } = meta;

  return (
    <div
      className={`
        w-[360px] h-[420px]
        bg-gradient-to-b from-[#11131a]/90 to-[#0c0c1a]/90
        backdrop-blur-md
        border-2 border-white-400
        rounded-xl
        shadow-[0_0_15px_rgba(255,255,255,0.4)]
        p-6
        flex flex-col justify-between
        font-mono text-white
      `}
    >
      {/* 상단: 이름 + 역할 */}
      <div>
        <h2 className="text-2xl font-extrabold tracking-wide uppercase text-white-400">
          {name}
        </h2>
        <p className="text-sm text-white/60 mt-1">
          ROLE: <span className="text-blue-400 font-bold">{role.toUpperCase()}</span>
        </p>
      </div>

      {/* 중단: (원하면 설명 추가 가능) */}
      {meta.description && (
      <p className="text-base text-white-100 font-semibold">
      {meta.description}
      </p>
      )}

      {/* 하단: 스탯 바 */}
      {stats && (
        <div className="space-y-4">
          <StatBar label="Power"   value={stats.power}   />
          <StatBar label="Logic"   value={stats.logic}   />
          <StatBar label="Empathy" value={stats.empathy} />
          <StatBar label="Speed"   value={stats.speed}   />
        </div>
      )}
    </div>
  );
}
