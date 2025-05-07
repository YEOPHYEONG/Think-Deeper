// src/features/select/components/TransitionOverlay.tsx
"use client";

import { motion } from "framer-motion";
import { useAgentStore } from "@/lib/store/agentStore";

export default function TransitionOverlay() {
  const showOv = useAgentStore(s => s.showOverlay);
    if (!showOv) return null;

    return (
      <motion.div
        className="fixed inset-0 z-50 bg-black flex items-center justify-center overflow-hidden"
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        style={{
          backgroundImage: "url(/img/effect/ink_splash.png)",
          backgroundSize: "1800px 1200px",
          backgroundRepeat: "no-repeat",
          backgroundPosition: "center",
          mixBlendMode: "screen",      
        }}
      />
    );
  }