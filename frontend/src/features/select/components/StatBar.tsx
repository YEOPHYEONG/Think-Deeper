// src/features/select/components/StatBar.tsx
"use client";
interface Props { label: string; value: number } // 0‑100
export default function StatBar({ label, value }: Props) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-20">{label}</span>
      <div className="flex-1 h-2 bg-gray-700 rounded">
        <div
          className="h-full bg-primary rounded"
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="w-8 text-right">{value}</span>
    </div>
  );
}
