// src/features/chat/types.ts
export interface ChatMessage {
    id: string;            // uuid
    role: "user" | "assistant";
    content: string;
    isStreaming?: boolean; // 응답 토큰이 아직 들어오는 중?
  }
  