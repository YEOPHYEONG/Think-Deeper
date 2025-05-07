"use client";
import { useEffect, useCallback } from "react";
import { useSelectStore } from "../store";
import { useAgentStore }  from "@/lib/store/agentStore";
import type { CharacterMeta } from "../types";

export const useSelectInput = (roster: CharacterMeta[]) => {
  const move = useSelectStore((s) => s.move);

  const handler = useCallback(
    (e: KeyboardEvent) => {
      const selState   = useSelectStore.getState();
      const agentState = useAgentStore.getState();
      const id = roster[selState.cursor]?.id;
      if (!id) return;

      switch (e.key) {
        // ←→↑↓ or WASD: 커서 이동
        case "ArrowUp": case "w": case "W":
          move("up");    e.preventDefault(); break;
        case "ArrowDown": case "s": case "S":
          move("down");  e.preventDefault(); break;
        case "ArrowLeft": case "a": case "A":
          move("left");  e.preventDefault(); break;
        case "ArrowRight": case "d": case "D":
          move("right"); e.preventDefault(); break;

        // Enter / Space: READY 토글
        case "Enter": case " ":
          agentState.toggleReady(id);
          e.preventDefault();
          break;

        // Esc / Backspace: READY 해제
        case "Escape": case "Backspace":
          agentState.unready(id);
          e.preventDefault();
          break;
      }
    },
    [move, roster],
  );

  useEffect(() => {
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handler]);
};
