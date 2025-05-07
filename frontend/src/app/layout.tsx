// src/app/layout.tsx

import './globals.css';
import type { Metadata } from 'next';
import Link from 'next/link';
import { Poppins } from 'next/font/google';
import BGMManager from '@/features/select/components/BGMManager';

// 로고용 폰트 설정
const poppins = Poppins({ subsets: ['latin'], weight: ['700'] });

export const metadata: Metadata = {
  title: 'Think Deeper',
  description: 'AI 기반 다각적 사고 증진 서비스',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-[#0c0c1a] text-slate-100 flex flex-col h-screen overflow-hidden">
        {/* 공통 헤더 */}
        <header
         className="
           fixed top-0 left-0 w-full
           py-4 px-6 bg-[#0c0c1a] border-b border-slate-700
           flex justify-center
           z-40
         "
       >
          <Link href="/" className={`${poppins.className} text-3xl text-indigo-400`}>
            Think Deeper
          </Link>
        </header>

        {/* 페이지별 콘텐츠: 헤더/푸터 제외한 공간을 flex로 채움 */}
        <main
       className="
          flex-1 flex flex-col min-h-0
           px-4 py-2
           pt-[64px]    /* 헤더 높이(px)만큼 패딩 추가 */
         "
       >  {/* 페이지 진입 시 BGMManager가 바로 마운트되어 자동 실행됩니다 */}
          <BGMManager />
          {children}
        </main>

        {/* 선택적 푸터 */}
        <footer className="flex-shrink-0 py-2 text-center text-slate-500 text-sm">
          © {new Date().getFullYear()} Think Deeper
        </footer>
      </body>
    </html>
  );
}
