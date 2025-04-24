// src/lib/api.ts

export interface Message {
  role: "user" | "assistant";
  content: string;
}

// API 서버 베이스 URL (환경 변수 우선, 없으면 로컬 호스트)
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

/**
 * 새 토론 세션을 생성하고 세션 ID를 반환합니다.
 * POST /api/v1/sessions
 */
export async function createSession(topic: string): Promise<string> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
  if (!res.ok) {
    throw new Error(`세션 생성 실패: ${res.status}`);
  }
  const data = await res.json();
  return data.session_id;
}

/**
 * 사용자 메시지를 서버에 전송하고 AI의 응답을 받아 반환합니다.
 * POST /api/v1/sessions/{sessionId}/message
 */
export async function sendMessage(
  sessionId: string,
  content: string
): Promise<string> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    throw new Error(`메시지 전송 실패: ${res.status}`);
  }
  const data = await res.json();
  return data.content;
}

/**
 * 해당 세션의 전체 메시지 히스토리를 불러옵니다.
 * GET /api/v1/sessions/{sessionId}/messages
 */
export async function fetchSessionMessages(
  sessionId: string
): Promise<Message[]> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
  if (!res.ok) {
    throw new Error(`세션 메시지 불러오기 실패: ${res.status}`);
  }
  return res.json();
}
