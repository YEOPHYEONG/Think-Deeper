// src/lib/api.ts

export interface Message {
  role: "user" | "assistant";
  content: string;
}

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
    timeoutMs = 60000, // 60초 타임아웃
  }: { method?: string; body?: any; timeoutMs?: number } = {}
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => {
      console.warn(`API Request timed out after ${timeoutMs}ms: ${method} ${path}`);
      controller.abort("Request timed out"); // 타임아웃 시 메시지 포함
  }, timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch(e) {
      // AbortError 또는 네트워크 오류 처리
      if (e instanceof DOMException && e.name === 'AbortError') {
         throw new ApiError(408, controller.signal.reason ?? 'Request timed out');
      }
      throw e; // 다른 네트워크 오류 등은 그대로 전파
  }
  finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    // 백엔드 오류 메시지 파싱 개선
    let errorData: any = null;
    try {
      errorData = await res.json();
    } catch { /* JSON 파싱 실패 시 무시 */ }
    const detail = errorData?.detail ?? res.statusText;
    const errorMessage = `HTTP ${res.status}: ${detail}`;
    console.error("API Error:", errorMessage, errorData); // 상세 로그 추가
    throw new ApiError(res.status, errorMessage);
  }

  // No Content 응답 처리 (세션 생성 등에서 필요할 수 있음)
  if (res.status === 204) {
      return {} as T; // 빈 객체 반환 (타입 주의)
  }

  // 성공 시 JSON 반환
  return (await res.json()) as T;
}

/**
 * 새 세션 생성 (초기 에이전트 타입 지정)
 */
export async function createSession(
  topic: string,
  agentType: string // agentType 인자 추가
): Promise<string> {
  // --- 요청 본문에 initial_agent_type 포함 ---
  const data = await request<{ session_id: string }>("/sessions", {
    method: "POST",
    body: { topic, initial_agent_type: agentType },
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
  // --- 타임아웃 값을 더 길게 설정할 수 있음 (예: 120초) ---
  const data = await request<Message>(`/sessions/${sessionId}/message`, {
    method: "POST",
    body: { content },
    timeoutMs: 120000 // 예: LLM 응답을 위해 120초로 늘림
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

/**
 * Why 모드에서 사용자 메시지 전송
 */
export async function sendWhyMessage(
  sessionId: string,
  content?: string
): Promise<Message> {
  const data = await request<{ response: string }>(
    `/sessions/${sessionId}/why`,
    {
      method: "POST",
      body: { input: content ?? "" },
      timeoutMs: 120000,
    }
  );
  return { role: "assistant", content: data.response };
}
