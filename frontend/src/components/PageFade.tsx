"use client";

import { motion, AnimatePresence } from "framer-motion";
import { usePathname } from "next/navigation";

export default function PageFade({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();          // 현재 경로 → key

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}                     // 경로 바뀔 때마다 새로 마운트
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.25, ease: "easeInOut" }}
        className="h-full flex flex-col"   // 부모(main)의 flex 공간 채움
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
