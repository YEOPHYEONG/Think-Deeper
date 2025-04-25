# backend/app/graph_nodes/coordinator.py
from typing import Dict, Any, Optional, List
import re

from ..models.graph_state import GraphState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from ..core.llm_provider import get_focus_llm # 포커스용 LLM 가져오기
from ..core import state_manager # 초기 정보 로드용 (임시)

async def determine_current_focus(last_ai_message: Optional[AIMessage], last_human_message: HumanMessage) -> Optional[str]:
    """ 마지막 AI 응답과 사용자 응답 기반으로 다음 턴 포커스 결정 (LLM 사용) """
    llm_for_focus = None
    try:
        llm_for_focus = get_focus_llm()
    except Exception as e:
        print(f"Coordinator(Focus): LLM 로드 실패 - {e}")
        return None # LLM 없으면 포커스 결정 불가

    if not last_ai_message:
        print("Coordinator(Focus): 이전 AI 메시지 없음, 포커스 결정 불가")
        return None

    try:
        focus_prompt = f"""... (포커스 결정 프롬프트 - 이전과 동일) ..."""
        print("Coordinator(Focus): 포커스 결정을 위한 LLM 호출")
        response = await llm_for_focus.ainvoke([SystemMessage(content=focus_prompt)])
        focus = response.content.strip()
        if focus.lower() == 'none' or len(focus) < 5: return None
        return focus[:150]
    except Exception as e:
        print(f"Coordinator(Focus): 포커스 결정 중 LLM 호출 오류 - {e}")
        return None

async def coordinator_node(state: GraphState) -> Dict[str, Any]:
    """ Coordinator 노드 (Target Agent 설정 및 라우팅 로직 반영) """
    print("--- Coordinator Node 실행 ---")
    try:
        messages: List[BaseMessage] = state.get('messages', [])
        session_id = state.get("session_id") # 상태에서 세션 ID 가져오기
        initial_topic = state.get("initial_topic", "주제 없음") # 상태에서 초기 주제 가져오기
        current_target_agent = state.get("target_agent") # 현재 타겟 에이전트 가져오기

        # --- 상태 초기화 및 target_agent 설정 ---
        if not messages: # 그래프 실행의 첫 번째 턴 (새 메시지 입력 직후)
            print("Coordinator: 첫 턴 또는 상태 초기화 감지")
            initial_info = None
            if session_id:
                initial_info = state_manager.get_session_initial_info(session_id) # 임시 저장소에서 정보 로드

            initial_target = initial_info.get("agent_type", "critic") if initial_info else "critic"
            initial_topic_from_store = initial_info.get("topic", "주제 없음") if initial_info else "주제 없음"

            initial_updates = {
                "mode": "OneOnOne", # 초기 모드를 1:1로 설정 (예시)
                "nuance": None, # 1:1 모드에서는 뉘앙스 불필요
                "critique_depth": 50, # 기본값
                "moderator_flags": [],
                "error_message": None,
                "current_focus": initial_topic_from_store,
                "target_agent": initial_target, # 로드하거나 기본값 사용
                "session_id": session_id,
                "initial_topic": initial_topic_from_store
            }
            print(f"Coordinator: 초기 상태 설정 반환 - {initial_updates}")
            return initial_updates

        # 마지막 메시지 확인 (이전과 동일)
        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage): return {}

        user_input_content = last_message.content

        # 상태 업데이트 준비 (현재 값으로 초기화)
        updates: Dict[str, Any] = {
            "mode": state.get("mode", "OneOnOne"), # 현재 모드 유지
            "nuance": state.get("nuance"),
            "critique_depth": state.get("critique_depth", 50),
            "moderator_flags": [],
            "error_message": None,
            "current_focus": state.get("current_focus"),
            "target_agent": current_target_agent # 현재 타겟 유지
        }
        command_detected = False

        # --- 명령어 감지 및 처리 (Agent 변경 등) ---
        if "/summarize" in user_input_content.lower():
            updates["moderator_flags"].append("summarize_request"); command_detected = True

        agent_match = re.search(r"/agent\s+(critic|advocate|why|socratic)", user_input_content, re.IGNORECASE)
        if agent_match:
             new_target_agent = agent_match.group(1).lower()
             updates["target_agent"] = new_target_agent
             updates["mode"] = "OneOnOne" # 에이전트 변경 시 모드도 설정
             updates["nuance"] = None
             command_detected = True; print(f"Coordinator: Target agent 변경됨 -> {new_target_agent}")

        # TODO: /mode, /depth 명령어 처리는 현재 OneOnOne 모드와 어떻게 연동될지 재정의 필요
        # depth_match = re.search(r"/depth\s+(\d+)", user_input_content) ...

        # --- 포커스 결정 (명령어 없을 시) ---
        if not command_detected and not updates.get("error_message"):
            last_ai_message = messages[-2] if len(messages)>1 and isinstance(messages[-2], AIMessage) else None
            new_focus = await determine_current_focus(last_ai_message, last_message)
            updates["current_focus"] = new_focus if new_focus else (updates["current_focus"] if updates["current_focus"] else initial_topic)
            print(f"Coordinator: Current focus 설정됨 -> '{updates['current_focus']}'")
        elif command_detected:
             updates["current_focus"] = None # 명령어 처리 시 포커스 초기화

        print(f"Coordinator: 상태 업데이트 반환 - { {k: v for k, v in updates.items() if v is not None} }")
        return {k: v for k, v in updates.items() if v is not None}

    except Exception as e:
        error_msg = f"Coordinator 노드 오류: {e}"
        import traceback; traceback.print_exc()
        return {"error_message": error_msg}