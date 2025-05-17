// src/features/select/store.ts
import { create } from "zustand";

type Dir = "up" | "down" | "left" | "right";

interface SelectState {
  cursor: number;          // 0~7
  ready:  boolean;
  setCursor: (i: number) => void;
  move:   (dir: Dir) => void;
  select: () => void;      // ready = true
  cancel: () => void;      // ready = false
}

export const useSelectStore = create<SelectState>((set) => ({
  cursor: 0,
  ready:  false,

  setCursor: (i) => set({ cursor: i }),

  move: (dir) =>
    set((s) => {
      const map: Record<Dir, number> = { up: -2, down: 2, left: -1, right: 1 };
      const next = (s.cursor + map[dir] + 4) % 4;
      return { cursor: next };
    }),

  /* Enter/Space 첫 입력 → 선택 확정 */
  select: ()   => set({ ready: true }),

  /* Esc/Backspace → 선택 취소 */
  cancel: ()   => set({ ready: false }),
}));
