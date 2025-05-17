// src/features/select/components/CharacterGrid.tsx
"use client";

import CharacterCard from "./CharacterCard";
import type { CharacterMeta } from "../types";

interface Props {
  roster: CharacterMeta[];
}

export default function CharacterGrid({ roster }: Props) {
  return (
    <div className="grid grid-cols-4 gap-4 h-full">
      {roster.map((c, i) => (
        <CharacterCard key={c.id} c={c} index={i} />
      ))}
    </div>
  );
}
