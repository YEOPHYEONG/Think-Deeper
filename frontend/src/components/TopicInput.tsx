// src/components/TopicInput.tsx

"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function TopicInput({ onStart }: { onStart: (topic: string) => void }) {
  const [topic, setTopic] = useState("");

  return (
    <div className="w-full max-w-xl mx-auto space-y-4">
      <h1 className="text-3xl text-slate-100 font-bold text-center">🧠 Think Deeper</h1>
      <p className="text-slate-400 text-center">주제를 입력하면, 우주의 지성들과 사고를 시작합니다.</p>
      <div className="flex gap-2">
      <Input
        placeholder="예: 기술 발전은 인간을 자유롭게 하는가?"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && topic.trim()) {
            onStart(topic);
          }
        }}
        className="bg-slate-900 text-slate-200"
      />
        <Button onClick={() => topic.trim() && onStart(topic)} className="bg-indigo-700 hover:bg-indigo-800 text-white">
          시작
        </Button>
      </div>
    </div>
  );
}
