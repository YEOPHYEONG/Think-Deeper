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
        # --- 포커스 결정 프롬프트 (내용은 이전과 동일) ---
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
        # --- ---
        print("Coordinator(Focus): 포커스 결정을 위한 LLM 호출")
        response = await llm_for_focus.ainvoke([SystemMessage(content=focus_prompt)])
        focus = response.content.strip()
        if focus.lower() == 'none' or len(focus) < 5: return None
        return focus[:150] # 최대 150자
    except Exception as e:
        print(f"Coordinator(Focus): 포커스 결정 중 LLM 호출 오류 - {e}")
        return None

async def coordinator_node(state: GraphState) -> Dict[str, Any]:
    """ Coordinator 노드 (Target Agent 설정 및 명령어 감지 로직 수정) """
    print("--- Coordinator Node 실행 ---")
    try:
        messages: List[BaseMessage] = state.get('messages', [])
        session_id = state.get("session_id")
        initial_topic = state.get("initial_topic", "주제 없음")
        current_target_agent = state.get("target_agent")

        # 상태 초기화 및 target_agent 설정 (이전과 동일)
        if not messages:
            print("Coordinator: 첫 턴 또는 상태 초기화 감지")
            initial_info = None
            if session_id:
                initial_info = state_manager.get_session_initial_info(session_id)

            initial_target = initial_info.get("agent_type", "critic") if initial_info else "critic"
            initial_topic_from_store = initial_info.get("topic", "주제 없음") if initial_info else "주제 없음"

            initial_updates = {
                "mode": "OneOnOne", "nuance": None, "critique_depth": 50,
                "moderator_flags": [], "error_message": None,
                "current_focus": initial_topic_from_store,
                "target_agent": initial_target,
                "session_id": session_id, "initial_topic": initial_topic_from_store
            }
            print(f"Coordinator: 초기 상태 설정 반환 - {initial_updates}")
            return initial_updates

        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage): return {}

        user_input_content = last_message.content
        # --- 명령어 감지를 위해 입력값의 앞뒤 공백 제거 및 소문자 변환 ---
        processed_input = user_input_content.strip().lower()

        # 상태 업데이트 준비 (이전과 동일)
        updates: Dict[str, Any] = {
            "mode": state.get("mode", "OneOnOne"), "nuance": state.get("nuance"),
            "critique_depth": state.get("critique_depth", 50),
            "moderator_flags": [], "error_message": None,
            "current_focus": state.get("current_focus"),
            "target_agent": current_target_agent
        }
        command_detected = False

        # --- 명령어 감지 로직 수정 ---
        # 1. /summarize 명령어: 정확히 일치할 때만 감지
        if processed_input == "/summarize":
            updates["moderator_flags"].append("summarize_request")
            command_detected = True
            print("Coordinator: /summarize 명령어 감지됨")

        # 2. /agent 명령어: 정확한 형식일 때만 감지
        #    (정규식 대신 startsWith 사용도 가능)
        agent_match = re.search(r"^/agent\s+(critic|advocate|why|socratic)$", processed_input, re.IGNORECASE)
        if agent_match:
             new_target_agent = agent_match.group(1).lower()
             updates["target_agent"] = new_target_agent
             updates["mode"] = "OneOnOne" # 에이전트 변경 시 모드 자동 설정
             updates["nuance"] = None
             command_detected = True; print(f"Coordinator: Target agent 변경됨 -> {new_target_agent}")

        # 3. /depth 명령어: 정확한 형식일 때만 감지
        depth_match = re.search(r"^/depth\s+(\d+)$", processed_input)
        if depth_match:
            try:
                new_depth = min(100, max(0, int(depth_match.group(1))))
                updates["critique_depth"] = new_depth
                # target_agent가 Critic일 때만 적용하거나, 모든 에이전트에 적용할지 결정 필요
                # if updates.get("target_agent") == "critic":
                #     updates["critique_depth"] = new_depth
                command_detected = True; print(f"Coordinator: Depth 변경됨 -> {new_depth}")
            except ValueError: pass
        # --- 명령어 감지 로직 수정 완료 ---

        # --- 포커스 결정 (명령어 없을 시) ---
        if not command_detected and not updates.get("error_message"):
            last_ai_message = messages[-2] if len(messages)>1 and isinstance(messages[-2], AIMessage) else None
            new_focus = await determine_current_focus(last_ai_message, last_message)
            # 이전 포커스가 있으면 유지, 없으면 초기 주제 사용
            updates["current_focus"] = new_focus if new_focus else (state.get("current_focus") if state.get("current_focus") else initial_topic)
            print(f"Coordinator: Current focus 설정됨 -> '{updates['current_focus']}'")
        elif command_detected:
             updates["current_focus"] = None # 명령어 처리 시 포커스 초기화

        # 상태 업데이트 반환 (None 값 제외)
        final_updates = {k: v for k, v in updates.items() if v is not None}
        print(f"Coordinator: 상태 업데이트 반환 - {final_updates}")
        return final_updates

    except Exception as e:
        error_msg = f"Coordinator 노드 오류: {e}"
        import traceback; traceback.print_exc()
        return {"error_message": error_msg}