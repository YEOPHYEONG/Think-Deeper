// src/features/select/components/SFXManager.ts
import { Howl } from "howler";
import { useSoundStore } from "@/lib/store/soundStore";

const sfx = {
  click: new Howl({ src: ["/audio/click.mp3"], volume: 0.1 }),
  hover: new Howl({ src: ["/audio/hover.mp3"], volume: 0.1 }), // ready 이벤트에 사용
  confirm: new Howl({ src: ["/audio/confirm.mp3"], volume: 0.05 }), // finish 이벤트에 사용
  // 필요한 효과음 키–파일명만 추가…
};

export function playSFX(name: keyof typeof sfx) {
    const { sfxEnabled } = useSoundStore.getState();
    if (!sfxEnabled) return;
    sfx[name]?.play();
}
