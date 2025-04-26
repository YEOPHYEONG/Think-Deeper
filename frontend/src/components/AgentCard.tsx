"use client";
import React from "react";
import { motion } from "framer-motion";
import { Agent } from "@/data/agents";

interface AgentCardProps {
  agent: Agent;
  isSelected: boolean;
  onClick: () => void;
}

export default function AgentCard({ agent, isSelected, onClick }: AgentCardProps) {
  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={`bg-white/10 border-2 rounded-2xl p-6 text-center shadow-lg backdrop-blur-md cursor-pointer transition-all ${
        isSelected ? "border-blue-400" : "border-white/20"
      }`}
    >
      <img
        src={agent.image}
        alt={agent.name}
        className="w-24 h-24 mx-auto mb-4 object-contain"
      />
      <h2 className="text-2xl font-semibold text-white mb-2">{agent.name}</h2>
      <p className="text-sm text-gray-300">{agent.description}</p>
    </motion.div>
  );
}