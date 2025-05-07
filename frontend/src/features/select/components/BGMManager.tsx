// src/features/select/components/BGMManager.tsx
"use client";

import { Howl } from "howler";
import { useEffect, useRef } from "react";
import { useSoundStore } from "@/lib/store/soundStore";

export default function BGMManager() {
  const howlRef = useRef<Howl | null>(null);
  const bgmEnabled = useSoundStore((s) => s.bgmEnabled);

  useEffect(() => {
    /* 1. Howl 인스턴스 생성 */
    howlRef.current = new Howl({
      src: ["/audio/select_theme.mp3"], // public/audio/ 경로
      loop: true,
      volume: 0.07,                       // 처음엔 0 → 페이드‑인
      html5: true,                    // 모바일 WebAudio 사용
    });

    /* 2. Safari 자동 재생 우회용 unlock */
    const unlock = () => {
      howlRef.current?.play();
      howlRef.current?.volume(0.07);
      window.removeEventListener("pointerdown", unlock);
    };
    // iOS는 사용자 제스처 필수, 데스크톱은 바로 재생
    if (/^((?!chrome|android).)*safari/i.test(navigator.userAgent)) {
      window.addEventListener("pointerdown", unlock, { once: true });
    } else unlock();

    return () => {
      howlRef.current?.stop();
    };
  }, []);

  // bgmEnabled 변경 시 페이드‑인/아웃
  useEffect(() => {
    if (!howlRef.current) return;
    if (bgmEnabled) {
      howlRef.current.play();
      howlRef.current.volume(0.07);
    } else {
      howlRef.current.pause();
    }
  }, [bgmEnabled]);

  return null;
}
