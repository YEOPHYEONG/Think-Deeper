"use client";                            // ⬅️ 추가 (클라이언트 컴포넌트化)

import PageFade from "@/components/PageFade";
import SelectScreen from "@/features/select/SelectScreen";

export default function SelectPage() {
  return (
    <PageFade>
      <SelectScreen />
    </PageFade>
  );
}
