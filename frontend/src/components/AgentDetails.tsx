"use client";
import React from "react";
import { Agent, roleNameMap } from "@/data/agents";

interface AgentDetailsProps {
  agent: Agent | null;
}

export default function AgentDetails({ agent }: AgentDetailsProps) {
  if (!agent) {
    return (
      <div className="p-6 bg-white/10 rounded-2xl text-gray-400 text-center">
        에이전트를 선택해주세요.
      </div>
    );
  }

  return (
    <div className="p-6 bg-white/10 rounded-2xl text-white backdrop-blur-md shadow-lg">
      <img
        src={agent.image}
        alt={agent.name}
        className="w-32 h-32 mx-auto mb-4 object-contain"
      />
      <h2 className="text-2xl font-semibold mb-2">{agent.name}</h2>
      <p className="text-sm text-gray-300">{agent.description}</p>
      <p className="mt-4 text-gray-200">역할: {roleNameMap[agent.role]}</p>
    </div>
  );
}
