"use client";
import React from "react";
import { roles, roleNameMap } from "@/data/agents";

interface RoleFilterProps {
  selectedRole: string | null;
  onRoleSelect: (role: string | null) => void;
}

export default function RoleFilter({ selectedRole, onRoleSelect }: RoleFilterProps) {
  return (
    <div className="flex justify-center gap-4">
      <button
        onClick={() => onRoleSelect(null)}
        className={`px-4 py-2 rounded-full transition-all ${
          !selectedRole
            ? "bg-blue-400 text-white"
            : "bg-white/20 text-gray-200"
        }`}
      >
        전체
      </button>
      {roles.map(role => (
        <button
          key={role}
          onClick={() => onRoleSelect(role)}
          className={`px-4 py-2 rounded-full transition-all ${
            selectedRole === role
              ? "bg-blue-400 text-white"
              : "bg-white/20 text-gray-200"
          }`}
        >
          {roleNameMap[role]}
        </button>
      ))}
    </div>
  );
}
