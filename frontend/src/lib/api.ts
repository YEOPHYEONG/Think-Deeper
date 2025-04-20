// src/lib/api.ts

const API_BASE = "http://localhost:8000/api/v1";

export async function createSession(topic: string): Promise<string> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });

  if (!res.ok) throw new Error("세션 생성 실패");
  const data = await res.json();
  return data.session_id;
}

export async function sendMessage(sessionId: string, content: string): Promise<string> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });

  if (!res.ok) throw new Error("메시지 전송 실패");
  const data = await res.json();
  return data.content;
}
