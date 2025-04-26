"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { agents, Agent, getAgentsByRole } from "@/data/agents";
import AgentCard from "@/components/AgentCard";
import AgentDetails from "@/components/AgentDetails";
import RoleFilter from "@/components/RoleFilter";
import { Button } from "@/components/ui/button";

export default function AgentSelectPage() {
  const [selectedAgents, setSelectedAgents] = useState<Agent[]>([]);
  const [selectedRole, setSelectedRole] = useState<Agent['role'] | null>(null);
  const [showIntro, setShowIntro] = useState(true);
  const [introDone, setIntroDone] = useState(false);
  const router = useRouter();

  const displayedAgents = selectedRole
    ? getAgentsByRole(selectedRole)
    : agents;

  const toggleAgent = (agent: Agent) => {
    setSelectedAgents(prev =>
      prev.find(a => a.name === agent.name)
        ? prev.filter(a => a.name !== agent.name)
        : [...prev, agent]
    );
  };

  const lastSelected = selectedAgents.at(-1) || null;

  useEffect(() => {
    const t1 = setTimeout(() => setShowIntro(false), 3000);
    const t2 = setTimeout(() => setIntroDone(true), 3100);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center p-8 overflow-hidden">
      {/* Background Video */}
      <motion.video
        initial={showIntro ? { scale: 1, opacity: 1 } : false}
        animate={showIntro ? { scale: 2, opacity: 0 } : { scale: 1, opacity: 1 }}
        transition={{ duration: 3, ease: "easeInOut" }}
        autoPlay loop muted playsInline
        poster="/background-placeholder.jpg"
        className={`fixed top-0 left-0 w-screen h-screen object-cover z-0 ${introDone ? "object-center" : ""}`}
      >
        <source src="/KakaoTalk_20250425_101815474.mp4" type="video/mp4" />
      </motion.video>

      {/* Overlay */}
      <div className="fixed top-0 left-0 w-screen h-screen bg-black/50 backdrop-blur-sm z-10" />

      {/* Header */}
      <AnimatePresence>
        {introDone && (
          <motion.div
            className="absolute top-8 w-full text-center z-30"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 1, delay: 0.2 }}
          >
            <h1 className="text-4xl font-bold text-white">🚀 Think Deeper: 에이전트 선택</h1>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content */}
      <AnimatePresence>
        {introDone && (
          <motion.div
            className="relative z-30 flex flex-col lg:flex-row items-start w-full max-w-7xl gap-8 mt-32"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 1, delay: 0.5 }}
          >
            <div className="flex-1">
              <RoleFilter selectedRole={selectedRole} onRoleSelect={setSelectedRole} />
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 mt-6">
                {displayedAgents.map(agent => (
                  <AgentCard
                    key={agent.name}
                    agent={agent}
                    isSelected={selectedAgents.some(a => a.name === agent.name)}
                    onClick={() => toggleAgent(agent)}
                  />
                ))}
              </div>
              {displayedAgents.length === 0 && (
                <div className="mt-8 text-center text-gray-400">선택한 역할에 해당하는 에이전트가 없습니다.</div>
              )}
              <div className="mt-10 text-center">
                <Button
                  disabled={selectedAgents.length === 0}
                  onClick={() => router.push(`/chat?agents=${selectedAgents.map(a => a.name).join(",")}`)}
                  className="px-6 py-3 text-lg bg-blue-500 hover:bg-blue-600 rounded-full"
                >
                  Start Session
                </Button>
              </div>
            </div>
            <div className="hidden lg:block w-96">
              <AgentDetails agent={lastSelected} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

