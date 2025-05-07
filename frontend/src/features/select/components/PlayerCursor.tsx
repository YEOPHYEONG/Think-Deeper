// src/features/select/components/PlayerCursor.tsx
"use client";

import { useSelectStore } from "@/features/select/store";

export default function PlayerCursor() {
  const cursor = useSelectStore((s) => s.cursor);
  const row = Math.floor(cursor / 4);
  const col = cursor % 4;

  return (
    <div
      className="absolute border-4 rounded-lg pointer-events-none z-10"
      style={{
        borderColor: "rgb(248, 113, 113)", // ✅ 연한 빨강
        width: "10rem",  // 카드 너비와 일치
        height: "12rem", // 카드 높이와 일치
        transform: `translate(${col * 10.5}rem, ${row * 12}rem)`,
        transition: "transform 150ms linear",
      }}
    >
      {/* 좌상단 1P 텍스트 (선택) */}
      <div
        style={{
          backgroundColor: "rgb(248, 113, 113)",
          color: "white",
          fontSize: "0.65rem",
          fontWeight: "bold",
          padding: "0.2rem 0.4rem",
          borderBottomRightRadius: "0.25rem",
        }}
      >
        1P
      </div>
    </div>
  );
}
