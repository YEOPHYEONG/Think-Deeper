# backend/app/graph_nodes/why/motivation_elicitation_node.py

from typing import Dict, Any, List, Optional, Union
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.types import interrupt # interrupt 임포트
from pydantic import BaseModel, Field # Pydantic 모델 사용

from ...core.llm_provider import get_high_performance_llm
from ...models.why_graph_state import WhyGraphState # 타입 힌팅용

class MotivationClarityOutput(BaseModel):
    is_motivation_clear: bool = Field(..., description="동기 명확 여부")
    clarification_question: Optional[str] = Field(None, description="불명확 시 추가 질문 또는 첫 질문")
    summary_of_motivation: Optional[str] = Field(None, description="명확 시 반환할 요약")

async def motivation_elicitation_node(state: Dict[str, Any]) -> Union[Dict[str, Any], None]:
    """
    Motivation Elicitation 노드:
    대화 이력을 기반으로 사용자의 동기 명확성을 판단하고,
    - 동기가 불명확하면 (첫 질문 포함) 추가 질문을 생성하여 interrupt 발생
    - 동기가 명확하면 요약을 생성하여 다음 노드로 상태 반환
    """
    print("[MOTIV][NODE_LIFECYCLE] Entering motivation_elicitation_node")

    messages: List[Union[BaseMessage, dict]] = state.get('messages', [])
    raw_topic: Optional[str] = state.get('raw_topic')
    raw_idea: Optional[str] = state.get('raw_idea')
    # has_asked_initial 플래그는 이제 이 노드에서 직접 사용하지 않고,
    # LLM이 대화 기록(messages)을 보고 첫 질문인지 후속 질문인지 판단하도록 유도합니다.
    # 다만, 오케스트레이터에서 이 플래그를 관리할 수 있도록 interrupt 데이터에는 포함합니다.

    llm = get_high_performance_llm()
    structured_llm = llm.with_structured_output(MotivationClarityOutput)

    system_prompt = (
        """
# 역할: 당신은 사용자의 아이디어와 그 이면의 동기를 깊이 탐구하는 AI 질문자입니다. 당신의 목표는 사용자가 자신의 핵심 동기('Why')를 명확히 하도록 돕는 것입니다.

# 핵심 지침:
1.  **대화 맥락 분석:** 제공된 대화 기록(`Dialogue History`)을 면밀히 분석하세요.
    * **첫 질문 생성 (대화 기록이 사용자 아이디어만 있는 경우 또는 비어 있는 경우):** 사용자가 제시한 초기 아이디어/주제를 바탕으로, 그 아이디어를 추진하게 만드는 가장 근본적인 동기, 목적, 또는 추구하는 가치('Why')에 대해 성찰하도록 유도하는 **단 하나의 통찰력 있는 개방형 질문**을 생성하세요. (예: "이 아이디어를 통해 궁극적으로 무엇을 성취하고 싶으신가요?", "이것이 왜 중요하다고 생각하시나요?")
    * **후속 질문 또는 명확성 판단 (이전 대화가 있는 경우):** 사용자의 이전 답변을 바탕으로 동기가 충분히 명확한지 평가하세요.
        * **불명확 시:** 사용자의 답변 내용 중 가장 불명확하거나 더 깊이 탐색해야 할 부분을 정확히 짚어내는 **단 하나의 구체적이고 통찰력 있는 후속 질문**을 생성하세요.
        * **명확 시:** 파악된 핵심 동기를 다음 단계를 위해 간결하게 요약하여 `summary_of_motivation`에 담고, `is_motivation_clear`를 `true`로 설정하세요. `clarification_question`은 `null`로 설정합니다.
2.  **질문/요약의 질:**
    * 질문은 사용자가 자신의 생각을 자세히 설명하도록 유도하는 개방형이어야 합니다.
    * 요약은 간결하고 명확해야 합니다.
3.  **구조화된 출력 형식:** 항상 `{"is_motivation_clear": boolean, "clarification_question": string | null, "summary_of_motivation": string | null}` 형식으로 결과를 출력하세요.

# 입력 예시 (user_prompt):
Dialogue History:
- User: 독자의 요구에 따라 실시간으로 소설을 써주는 ai야.
- Assistant: 그 아이디어를 통해 궁극적으로 무엇을 성취하고 싶으신가요?
- User: 사용자들이 더 몰입감 있는 스토리를 경험했으면 좋겠어요.

# 출력 지침: 위 역할과 지침에 따라, 제공된 대화 기록을 분석하여 판단하고, 필요한 질문 또는 요약을 포함한 JSON 객체를 생성하세요.
        """.strip()
    )

    history_lines = []
    current_messages_for_state_update = []

    for i, msg_data in enumerate(messages):
        role = None
        content = None
        msg_obj = None

        if isinstance(msg_data, HumanMessage):
            role, content, msg_obj = "User", msg_data.content, msg_data
        elif isinstance(msg_data, AIMessage):
            role, content, msg_obj = "Assistant", msg_data.content, msg_data
        elif isinstance(msg_data, dict):
            msg_type = msg_data.get("type")
            raw_content_from_dict = msg_data.get("content")
            add_kwargs = msg_data.get("additional_kwargs", {})
            if raw_content_from_dict is not None:
                if msg_type == "human":
                    role, content = "User", raw_content_from_dict
                    msg_obj = HumanMessage(content=content, additional_kwargs=add_kwargs)
                elif msg_type == "ai" or msg_type == "assistant":
                    role, content = "Assistant", raw_content_from_dict
                    msg_obj = AIMessage(content=content, additional_kwargs=add_kwargs)
        
        if role and content is not None:
            history_lines.append(f"- {role}: {content}")
        
        if msg_obj:
            current_messages_for_state_update.append(msg_obj)
        elif isinstance(msg_data, dict) and msg_data.get("content") is not None :
             current_messages_for_state_update.append(msg_data)

    user_prompt_content = "Dialogue History:\n" + "\n".join(history_lines) if history_lines \
                          else f"Initial Idea/Topic: {raw_idea or raw_topic or 'Not provided'}"

    print(f"  [MOTIV][DEBUG] user_prompt to LLM:\n{user_prompt_content}")

    try:
        print("  [MOTIV][INFO] Calling LLM for motivation clarity/question...")
        llm_response: MotivationClarityOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt_content)
        ])
        print(f"  [MOTIV][DEBUG] LLM response (resp): {llm_response}")
        print("  [MOTIV][INFO] LLM call completed.")
    except Exception as e:
        print(f"  [MOTIV][ERROR] LLM call failed: {e}")
        error_question = f"(시스템 오류: 동기 판단/질문 생성 중 문제가 발생했습니다. {e})"
        # AI의 오류 메시지도 messages에 추가
        updated_error_messages = current_messages_for_state_update + [AIMessage(content=error_question)]
        error_interrupt_data = {
            "messages": updated_error_messages,
            "motivation_cleared": False,
            "has_asked_initial": True, 
            "error_message": f"LLM Error in motivation_elicitation: {str(e)}",
            "clarification_question": error_question
        }
        print(f"  [MOTIV][DEBUG] Data for error interrupt: {error_interrupt_data}")
        print(f"[MOTIV][NODE_LIFECYCLE] Exiting motivation_elicitation_node with interrupt (error): {error_question}")
        raise interrupt(error_question).with_data(error_interrupt_data)

    if not llm_response.is_motivation_clear:
        clarification_q_str = llm_response.clarification_question or "(질문 생성 실패)"
        print(f"  [MOTIV][DEBUG] Motivation unclear or first question -> raising interrupt with question: {clarification_q_str}")
        
        updated_messages_with_ai_q = current_messages_for_state_update + [AIMessage(content=clarification_q_str)]
        
        interrupt_data_for_question = {
            "messages": updated_messages_with_ai_q, # AI 질문이 포함된 전체 메시지 리스트
            "motivation_cleared": False,
            "has_asked_initial": True, 
            "error_message": None,
            "clarification_question": clarification_q_str
        }
        # --- 추가된 로그 ---
        print(f"  [MOTIV][DEBUG] Data for question interrupt (interrupt_data_for_question):")
        print(f"    - messages (last 2): {[m.content if isinstance(m, BaseMessage) else m for m in updated_messages_with_ai_q[-2:]]}")
        print(f"    - has_asked_initial: {interrupt_data_for_question.get('has_asked_initial')}")
        print(f"    - clarification_question: {interrupt_data_for_question.get('clarification_question')}")
        # --- ---
        print(f"[MOTIV][NODE_LIFECYCLE] Exiting motivation_elicitation_node with interrupt (question): {clarification_q_str}")
        raise interrupt(clarification_q_str).with_data(interrupt_data_for_question)
    else:
        summary_msg_str = llm_response.summary_of_motivation or "(동기 요약 정보 없음)"
        print(f"  [MOTIV][DEBUG] Motivation clear -> returning summary state: {summary_msg_str}")
        
        updated_messages_with_summary = current_messages_for_state_update + [AIMessage(content=summary_msg_str)]

        state_update_on_clear = {
            "messages": updated_messages_with_summary, # AI 요약이 포함된 전체 메시지 리스트
            "motivation_cleared": True,
            "final_motivation_summary": summary_msg_str,
            "has_asked_initial": True, 
            "error_message": None,
            "clarification_question": None
        }
        # --- 추가된 로그 ---
        print(f"  [MOTIV][DEBUG] Data for state_update_on_clear:")
        print(f"    - messages (last 2): {[m.content if isinstance(m, BaseMessage) else m for m in updated_messages_with_summary[-2:]]}")
        print(f"    - has_asked_initial: {state_update_on_clear.get('has_asked_initial')}")
        print(f"    - motivation_cleared: {state_update_on_clear.get('motivation_cleared')}")
        # --- ---
        print(f"[MOTIV][NODE_LIFECYCLE] Exiting motivation_elicitation_node with state update.")
        return state_update_on_clear
