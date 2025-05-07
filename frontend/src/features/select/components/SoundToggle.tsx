// src/components/SoundToggle.tsx
"use client";

import { useSoundStore } from "@/lib/store/soundStore";

export default function SoundToggle() {
  const { sfxEnabled, bgmEnabled, toggleSfx, toggleBgm } = useSoundStore();
  return (
    <div className="flex gap-4 items-center p-2">
      <button
        onClick={toggleBgm}
        className="px-3 py-1 border rounded"
      >
        배경음: {bgmEnabled ? "On" : "Off"}
      </button>
      <button
        onClick={toggleSfx}
        className="px-3 py-1 border rounded"
      >
        효과음: {sfxEnabled ? "On" : "Off"}
      </button>
    </div>
  );
}
