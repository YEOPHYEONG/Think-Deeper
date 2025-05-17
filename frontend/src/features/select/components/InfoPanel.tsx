// src/features/select/components/InfoPanel.tsx
"use client";

import type { CharacterMeta } from "../types";

interface Props {
  meta: CharacterMeta;
}

export default function InfoPanel({ meta }: Props) {
  const { name, role, description } = meta;

  return (
    <div
      className={`
        w-[280px]
        bg-gradient-to-b from-[#7c86ff]/30 to-[#0c0c1a]/50
        backdrop-blur-md
        border-3 border-white/50
        rounded-xl
        shadow-[0_0_15px_rgba(255,255,255,0.2)]
        p-4
        flex flex-col gap-2
        font-mono text-white
      `}
    >
      {/* 이름 + 역할 */}
      <div>
        <h2 className="text-xl font-extrabold tracking-wide uppercase text-white">
          {name}
        </h2>
        <p className="text-sm text-white/60 mt-1">
          ROLE: <span className="text-blue-400 font-bold">{role.toUpperCase()}</span>
        </p>
      </div>

      {/* 설명 */}
      {description && (
        <p className="text-sm text-white/90 leading-relaxed">
          {description}
        </p>
      )}
    </div>
  );
}
