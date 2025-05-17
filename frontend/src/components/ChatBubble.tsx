// src/components/ChatBubble.tsx

import React from "react";
import ReactMarkdown from "react-markdown";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { motion } from "framer-motion";

export type ChatRole = "user" | "assistant";

interface ChatBubbleProps {
  role: ChatRole;
  content: string;
  agentType?: string;
}

export function ChatBubble({ role, content, agentType }: ChatBubbleProps) {
  const isUser = role === "user";
  const avatarSrc = isUser
    ? "/characters/user.png"
    : `/characters/${agentType || "ai"}.png`;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-6 md:mb-8 w-full`}
    >
      {!isUser && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring" }}
        >
          <Avatar className="mr-2 h-12 w-12">
            <AvatarImage src={avatarSrc} alt="AI 캐릭터" className="object-cover" />
            <AvatarFallback className="bg-indigo-600">🤖</AvatarFallback>
          </Avatar>
        </motion.div>
      )}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.2 }}
        className={`max-w-[80%] p-4 rounded-2xl whitespace-pre-wrap prose prose-invert text-base font-medium drop-shadow-lg border
          ${isUser 
            ? "bg-indigo-300/30 text-white rounded-br-none hover:bg-indigo-950 transition-colors ml-8 md:ml-16 border-indigo-800/80" 
            : "bg-indigo-900/50 text-white rounded-bl-none hover:bg-indigo-950 transition-colors mr-8 md:mr-16 border-indigo-800/80"}`}
      >
        <ReactMarkdown
          components={{
            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
            ul: ({ children }) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
            li: ({ children }) => <li className="mb-1">{children}</li>,
            code: ({ children }) => (
              <code className="bg-slate-700/50 px-1.5 py-0.5 rounded text-xs font-mono hover:bg-slate-600/50 transition-colors">
                {children}
              </code>
            ),
            pre: ({ children }) => (
              <pre className="bg-slate-700/50 p-2 rounded-lg overflow-x-auto mb-2 hover:bg-slate-600/50 transition-colors">
                {children}
              </pre>
            ),
            a: ({ href, children }) => (
              <a 
                href={href} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-indigo-400 hover:text-indigo-300 underline transition-colors"
              >
                {children}
              </a>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </motion.div>
      {isUser && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring" }}
        >
          <Avatar className="ml-2 h-12 w-12">
            <AvatarImage src={avatarSrc} alt="User 캐릭터" className="object-cover" />
            <AvatarFallback className="bg-slate-700">👤</AvatarFallback>
          </Avatar>
        </motion.div>
      )}
    </motion.div>
  );
}
