// src/features/select/components/InfoPanel.tsx
"use client";

import StatBar from "./StatBar";
import type { CharacterMeta } from "../types";

interface Props {
  meta: CharacterMeta;
}

export default function InfoPanel({ meta }: Props) {
  const { stats, country, name, role } = meta;

  return (
    <div className="flex flex-col sm:flex-row gap-4 p-4 bg-[#1a1a2e] rounded-lg w-full max-w-2xl">
      <div className="flex-1 flex flex-col justify-center">
        <div className="flex items-center gap-2 mb-2">
          <img
            src={`/flags/${country}.svg`}
            alt={country}
            className="w-6"
          />
          <h2 className="text-xl font-bold">{name}</h2>
        </div>
        <p className="text-sm text-amber-300 mb-4">{role}</p>

        {stats && (
          <div className="space-y-2">
            <StatBar label="Power" value={stats.power} />
            <StatBar label="Logic" value={stats.logic} />
            <StatBar label="Empathy" value={stats.empathy} />
            <StatBar label="Speed" value={stats.speed} />
          </div>
        )}
      </div>
    </div>
  );
}
