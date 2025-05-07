// src/features/select/components/CharacterGrid.tsx
"use client";

import CharacterCard from "./CharacterCard";
import type { CharacterMeta } from "../types";

interface Props {
  roster: CharacterMeta[];
}

export default function CharacterGrid({ roster }: Props) {
  return (
  
      /* 캐릭터 카드들 */
      <div className="grid grid-cols-4 gap-6">
      {roster.map((c, i) => (
        <CharacterCard key={c.id} c={c} index={i} />
      ))}
    </div>
  );
}
