// src/features/select/types.ts
export interface CharacterStats {
  power: number;   // 0‑100
  logic: number;
  empathy: number;
  speed: number;
}

export interface CharacterMeta {
  id: string;
  name: string;
  role: string;
  country: string;
  portrait: string;
  model?: string;        // 3D GLB 경로 (선택)
  stats?: CharacterStats;
  description?: string;
}
