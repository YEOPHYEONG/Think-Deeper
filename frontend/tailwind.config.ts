import type { Config } from "tailwindcss";

/** @type {import('tailwindcss').Config} */
export default {
  // 1) Tailwind가 스캔할 파일 경로
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
  ],

  // 2) 토큰 확장
  theme: {
    extend: {
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
      colors: {
        primary: "#7c86ff",        // 핵심 포인트색 (indigo-500)
        surface: "#1e1e2e",        // 카드/버튼 기본 배경
        "surface-hover": "#26263A" // 호버 배경
      },
      dropShadow: {
        glow: "0 0 8px #6366F1, 0 0 12px #6366F1",  // 글로우용
      },
      borderRadius: {
        lg: "0.75rem",             // 카드 둥글기
      },
      perspective: {
        '1000': '1000px',
      },
      transformStyle: {
        '3d': 'preserve-3d',
      },
      backfaceVisibility: {
        'hidden': 'hidden',
      },
      rotate: {
        'y-180': 'rotateY(180deg)',
      },
    },
  },

  // 3) 플러그인 섹션(없으면 빈 배열)
  plugins: [],
} satisfies Config;
