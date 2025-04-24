# backend/app/graph_nodes/coordinator.py
from typing import Dict, Any, Optional, List
import re

# GraphState 모델 및 LangChain 메시지 타입 임포트
from ..models.graph_state import GraphState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI # LLM 클라이언트

# 설정 로드 (LLM 사용 위함)
from ..core.config import get_settings
settings = get_settings()

# LLM 클라이언트 초기화 (focus 결정용 - 빠른 모델 권장)
try:
    # orchestration.py 와 중복 정의 -> 개선 필요
    llm_fast = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=settings.OPENAI_API_KEY) # 낮은 temperature로 일관성 확보
    print("Coordinator Node: Focus용 LLM 클라이언트 초기화 성공")
except Exception as e:
    print(f"Coordinator Node: Focus용 LLM 클라이언트 초기화 실패 - {e}")
    llm_fast = None


async def determine_current_focus(last_ai_message: Optional[AIMessage], last_human_message: HumanMessage) -> Optional[str]:
    """
    (비동기 함수로 변경 가능성 있음)
    마지막 AI 응답과 사용자 응답을 바탕으로 다음 턴의 핵심 포커스를 결정합니다.
    (LLM 호출 방식 사용)
    """
    if not llm_fast:
        print("Coordinator(Focus): LLM 클라이언트 없음, 포커스 결정 불가")
        return None
    if not last_ai_message:
        print("Coordinator(Focus): 이전 AI 메시지 없음, 포커스 결정 불가")
        return None # 초기 턴 등 이전 AI 메시지 없으면 포커스 없음

    try:
        focus_prompt = f"""
당신은 대화의 핵심 논점을 파악하는 분석가입니다. 다음은 AI(Critic/Facilitator)의 마지막 응답과 그에 대한 사용자의 응답입니다. 이 사용자 응답이 주로 어떤 핵심 질문이나 논점에 대해 답변하고 있는지, 또는 다음 대화에서 가장 중요하게 다뤄져야 할 주제가 무엇인지 **하나의 짧은 구(phrase)나 질문 형태**로 요약해주세요. 사용자의 의도를 파악하는 것이 중요합니다. 만약 명확한 초점을 찾기 어렵다면 'None'을 반환하세요.

AI의 마지막 응답:
---
{last_ai_message.content}
---

사용자의 응답:
---
{last_human_message.content}
---

다음 대화의 핵심 초점 (짧은 구 또는 질문 형태):"""

        print("Coordinator(Focus): 포커스 결정을 위한 LLM 호출")
        response = await llm_fast.ainvoke([SystemMessage(content=focus_prompt)]) # 비동기 호출 사용 고려
        focus = response.content.strip()
        print(f"Coordinator(Focus): LLM 결과 - '{focus}'")

        if focus.lower() == 'none' or len(focus) < 5: # 너무 짧거나 None이면 무시
            return None
        # 필요시 추가 정제 로직 (예: 너무 길면 자르기)
        return focus[:150] # 최대 150자 제한 (임의)

    except Exception as e:
        print(f"Coordinator(Focus): 포커스 결정 중 오류 - {e}")
        return None


async def coordinator_node(state: GraphState) -> Dict[str, Any]: # async로 변경
    """
    Coordinator 노드: 사용자 입력을 처리하고, 상태를 업데이트하며,
    명령어(/mode, /depth, /summarize)를 감지하고, 다음 실행할 노드를 결정합니다.
    LLM을 사용하여 다음 Critic 턴을 위한 현재 포커스를 설정합니다.
    """
    print("--- Coordinator Node 실행 ---")

    try:
        messages: List[BaseMessage] = state.get('messages', [])
        initial_topic = state.get("initial_topic", "초기 주제") # 세션 생성 시 주제 활용

        # 초기 상태 처리 (메시지 없음)
        if not messages:
            print("Coordinator: 메시지 리스트가 비어있음 (초기 상태)")
            initial_updates = {
                "mode": "Standard",
                "nuance": "Debate",
                "critique_depth": 50,
                "moderator_flags": [],
                "error_message": None,
                "current_focus": initial_topic
            }
            print(f"Coordinator: 초기 상태 설정 - {initial_updates}")
            return initial_updates

        # 마지막 메시지가 사용자 입력인지 확인
        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage):
            print("Coordinator: 경고 - 마지막 메시지가 HumanMessage 타입이 아님. 상태 업데이트 건너뜀.")
            return {} # 상태 변경 없음

        user_input_content = last_message.content

        # 상태 업데이트 준비 (기존 값으로 초기화)
        current_mode = state.get("mode", "Standard")
        current_nuance = state.get("nuance", "Debate")
        current_depth = state.get("critique_depth", 50)
        current_focus_from_state = state.get("current_focus") # 이전 포커스
        updates: Dict[str, Any] = {
            "mode": current_mode,
            "nuance": current_nuance,
            "critique_depth": current_depth,
            "moderator_flags": [],
            "error_message": None,
            "current_focus": current_focus_from_state # 일단 유지
        }
        command_detected = False

        # --- 명령어 감지 및 처리 ---
        # (이전과 동일한 /summarize, /mode, /depth 처리 로직)
        # ... (생략 - 이전 코드 내용과 동일) ...
        if "/summarize" in user_input_content.lower():
            updates["moderator_flags"].append("summarize_request")
            command_detected = True
        if not command_detected:
            mode_match = re.search(r"/mode\s+(standard|fastdebate)", user_input_content, re.IGNORECASE)
            if mode_match:
                # ... /mode 처리 ...
                command_detected = True
            depth_match = re.search(r"/depth\s+(\d+)", user_input_content)
            if depth_match:
                # ... /depth 처리 ...
                command_detected = True


        # --- 점진적 대화를 위한 현재 포커스 결정 (LLM 사용) ---
        if not command_detected and not updates.get("error_message"):
            # 이전 AI 메시지 찾기
            last_ai_message: Optional[AIMessage] = None
            if len(messages) > 1 and isinstance(messages[-2], AIMessage):
                last_ai_message = messages[-2]

            # LLM 호출하여 포커스 결정 (비동기 호출)
            new_focus = await determine_current_focus(last_ai_message, last_message)

            if new_focus:
                 updates["current_focus"] = new_focus
                 print(f"Coordinator: Current focus 설정 (LLM) - '{new_focus}'")
            else:
                 # LLM이 포커스를 결정하지 못하면 이전 포커스 유지 또는 초기 주제 사용
                 updates["current_focus"] = current_focus_from_state if current_focus_from_state else initial_topic
                 print(f"Coordinator: LLM 포커스 결정 실패, 이전/초기 포커스 유지 - '{updates['current_focus']}'")

        elif command_detected:
             # 명령어 처리 후 포커스 초기화 또는 유지 정책 결정
             updates["current_focus"] = None # 예: 명령어 후 포커스 초기화
             print("Coordinator: 명령어 처리 후 포커스 초기화")

        # --- (선택적) 입력 포맷팅 ---
        # TODO: Formatting 노드/헬퍼 호출 로직 추가

        print(f"Coordinator: 상태 업데이트 반환 - Mode={updates['mode']}, Nuance={updates.get('nuance')}, Depth={updates['critique_depth']}, Flags={updates['moderator_flags']}, Focus={updates.get('current_focus')}, Error={updates.get('error_message')}")
        final_updates = {k: v for k, v in updates.items() if v is not None}
        return final_updates

    except Exception as e:
        error_msg = f"Coordinator 노드 심각한 오류 발생: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {"error_message": error_msg}