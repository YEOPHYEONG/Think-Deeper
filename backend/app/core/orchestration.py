# backend/app/core/orchestration.py
# 필요한 임포트 추가/수정
from autogen_agentchat.agents import UserProxyAgent, AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
# 종료 조건 임포트
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.messages import TextMessage # task 전달용
from autogen_agentchat.base import TaskResult      # run 결과 타입
# 모델 클라이언트 임포트
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
# ... (다른 필요한 클라이언트 임포트)
from typing import Dict, Any, Optional, List

from ..core.config import get_settings
from ..agents.critic import create_critic_agent
from ..core import state_manager

settings = get_settings()

# --- 모델 클라이언트 가져오는 함수 (이전과 동일, 필요시 개선) ---
def get_model_client(model_name: str = "o4-mini") -> Optional[ChatCompletionClient]:
    # ... (이전 코드 내용) ...
    api_model_id_map = {
        "gpt-4.1": "gpt-4.1-2025-04-14", # Placeholder
        "gpt-4.1-mini": "gpt-4.1-mini-2025-04-14", # Placeholder
        "gpt-4.1-nano": "gpt-4.1-nano-2025-04-14", # Placeholder
        "o4-mini": "o4-mini-2025-04-16", # Placeholder
        "gemini-2.5-pro": "gemini-2.5-pro-preview", # Placeholder
        "gemini-2.5-flash": "gemini-2.5-flash-preview",# Placeholder
        "gemini-2.0-flash": "gemini-2.0-flash",       # Placeholder
        "claude-3.7-sonnet": "claude-3.7-sonnet",    # Placeholder
        "claude-3.5-sonnet": "claude-3.5-sonnet",    # Placeholder
        "claude-3.5-haiku":  "claude-3.5-haiku",     # Placeholder
    }
    api_model_id = api_model_id_map.get(model_name, "gpt-4.1-2025-04-14")
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        print("오류: OPENAI_API_KEY가 설정되지 않았습니다.")
        return None

    try:
        # o4‑mini 계열만 기본 temperature(1) 사용
        if api_model_id.startswith("o4-mini"):
            client = OpenAIChatCompletionClient(
                model=api_model_id,
                api_key=api_key
            )
        else:
            client = OpenAIChatCompletionClient(
                model=api_model_id,
                api_key=api_key,
                temperature=0.7
            )
        print(f"OpenAI 클라이언트 생성됨 (모델: {api_model_id})")
        return client
    except Exception as e:
        print(f"OpenAI 클라이언트 생성 오류: {e}")
        return None

# --- 메인 오케스트레이션 함수 (Gemini 답변 기반 수정) ---
async def run_conversation_turn(session_id: str, user_input: str) -> Optional[str]:
    print(f"사용자 메시지: {user_input}")
    # 1) 모델 클라이언트 준비
    model_client = get_model_client("o4-mini")
    if not model_client:
        raise RuntimeError("모델 클라이언트 생성 실패")

    # 2) 에이전트 생성
    critic_agent = create_critic_agent(model_client=model_client)

    # 3) 종료 조건 & 팀 구성
    termination_condition = SourceMatchTermination([critic_agent.name])
    team = RoundRobinGroupChat(
        participants=[critic_agent],
        termination_condition=termination_condition,  # ← 앞에서 만든 변수 재사용
        max_turns=1,
    )

    # 4) 이전 상태 로드
    saved_state = state_manager.get_session_autogen_state(session_id)
    if saved_state:
        team.load_state(saved_state)

    # 5) 사용자 메시지(task) 구성
    from autogen_agentchat.messages import TextMessage

    task_message = TextMessage(
        content=user_input,            # ← 여기로 변경
        source="User"
    )
    task_result: TaskResult = await team.run(task=task_message)
    
    # 7) Critic 응답 추출
    critic_response = None
    for msg in task_result.messages:
        if getattr(msg, "source", None) == critic_agent.name:
            critic_response = msg.content
    if critic_response is None:
        critic_response = "오류: Critic 응답을 찾을 수 없음"

    # 8) 상태 저장
    new_state = team.save_state()
    state_manager.save_session_autogen_state(session_id, new_state)

    return critic_response
