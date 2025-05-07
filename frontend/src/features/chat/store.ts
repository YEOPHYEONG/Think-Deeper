import { create } from "zustand";
import { v4 as uuid } from "uuid";
import type { ChatMessage } from "./types";

type ChatState = {
  messages: ChatMessage[];

  /** 사용자 메시지를 추가하고 id 반환 */
  addUser: (text: string) => string;

  /** 빈 assistant 메시지를 만든 뒤 id 반환 */
  addAssistant: () => string;

  /** assistant 토큰 1개씩 이어붙이기 */
  appendToken: (id: string, token: string) => void;

  /** 스트리밍 종료 */
  finishAssistant: (id: string) => void;
};

export const useChatStore = create<ChatState>((set) => ({
  messages: [],

  addUser: (text) => {
    const id = uuid();
    set((s) => ({
      messages: [...s.messages, { id, role: "user", content: text }],
    }));
    return id;
  },

  addAssistant: () => {
    const id = uuid();
    set((s) => ({
      messages: [
        ...s.messages,
        { id, role: "assistant", content: "", isStreaming: true },
      ],
    }));
    return id;
  },

  appendToken: (id, token) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m,
      ),
    })),

  finishAssistant: (id) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, isStreaming: false } : m,
      ),
    })),
}));
