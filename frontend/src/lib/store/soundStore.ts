// src/lib/store/soundStore.ts
import { create } from "zustand";

interface SoundState {
  sfxEnabled: boolean;
  bgmEnabled: boolean;
  toggleSfx: () => void;
  toggleBgm: () => void;
}

export const useSoundStore = create <SoundState> ((set) => ({
  sfxEnabled: true,
  bgmEnabled: true,
  toggleSfx: () => set((s) => ({ sfxEnabled: !s.sfxEnabled })),
  toggleBgm: () => set((s) => ({ bgmEnabled: !s.bgmEnabled })),
}));
