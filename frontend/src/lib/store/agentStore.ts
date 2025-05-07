import { create } from "zustand";

interface AgentState {
  readyIds: string[];

  /** 마우스 클릭 or Enter/Space: READY 토글 */
  toggleReady: (id: string) => void;

  ready: (id: string) => void;

  /** Esc/Backspace: READY 해제 */
  unready: (id: string) => void;

 /** 모든 ready 상태 초기화 */
 reset: () => void;
 /** 페이지 진입 시 readyIds 를 비워줄 때 쓰세요 */
 clearReady: () => void;
 /** Next 누르면 Overlay 보여줄지 */
  showOverlay: boolean;
  setShowOverlay: (v: boolean) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  readyIds: [],

  toggleReady: (id) =>
    set((s) =>
      s.readyIds.includes(id)
        ? { readyIds: s.readyIds.filter((x) => x !== id) }
        : { readyIds: [...s.readyIds, id] }
    ),
    
  // 🆕 키보드 Enter/Space 용
  ready: (id) =>
    set((s) =>
      s.readyIds.includes(id) ? s : { readyIds: [...s.readyIds, id] }
    ),  

  unready: (id) =>
    set((s) => ({ readyIds: s.readyIds.filter((x) => x !== id) })),

  reset: () => set({ readyIds: [] }),
  clearReady: () => set({ readyIds: [] }),
  showOverlay: false,
  setShowOverlay: (v) => set({ showOverlay: v }),
}));
