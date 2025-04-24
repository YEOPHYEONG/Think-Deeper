// src/lib/api.ts

export interface Message {
  role: "user" | "assistant";
  content: string;
}

/**
 * API 호출 중 상태 코드, 에러 메시지, 타임아웃/취소를 
 * 일관되게 처리하는 공통 헬퍼
 */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

async function request<T>(
  path: string,
  {
    method = "GET",
    body,
    timeoutMs = 10000, // 10초 타임아웃
  }: { method?: string; body?: any; timeoutMs?: number } = {}
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    const errorText = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, `HTTP ${res.status}: ${errorText}`);
  }

  return (await res.json()) as T;
}

/**
 * 새 세션 생성
 */
export async function createSession(
  topic: string
): Promise<string> {
  const data = await request<{ session_id: string }>("/sessions", {
    method: "POST",
    body: { topic },
  });
  return data.session_id;
}

/**
 * 사용자 메시지 전송 후, assistant의 응답 메시지 전체 반환
 */
export async function sendMessage(
  sessionId: string,
  content: string
): Promise<Message> {
  const data = await request<Message>(`/sessions/${sessionId}/message`, {
    method: "POST",
    body: { content },
  });
  return data;
}

/**
 * 해당 세션의 전체 메시지 히스토리 반환
 */
export async function fetchSessionMessages(
  sessionId: string
): Promise<Message[]> {
  return await request<Message[]>(`/sessions/${sessionId}/messages`, {
    method: "GET",
  });
}
