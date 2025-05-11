// src/features/select/components/StatBar.tsx
"use client";

interface Props {
  label: string;
  value: number; // 0–100
}

export default function StatBar({ label, value }: Props) {
  // 라벨별 게이지 색상 매핑
  let color = "#fff";
  switch (label.toLowerCase()) {
    case "power":
      color = "#dc2626"; break; // red-600
    case "logic":
      color = "#2563eb"; break; // blue-600
    case "empathy":
      color = "#e879f9"; break; // pink-400
    case "speed":
      color = "#10b981"; break; // green-500
  }

  return (
    <div className="flex items-center gap-2">
      <span className="w-20 text-sm text-white/70 uppercase">{label}</span>
      <div className="flex-1 h-3 bg-white/10 rounded overflow-hidden">
        <div
          className="h-full transition-all duration-300"
          style={{
            width: `${value}%`,
            backgroundColor: color,
            boxShadow: `0 0 6px ${color}`,
          }}
        />
      </div>
      <span className="w-8 text-right text-sm font-bold">{value}</span>
    </div>
  );
}
