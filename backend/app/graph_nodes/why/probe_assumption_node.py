# backend/app/graph_nodes/why/probe_assumption_node.py

from typing import Dict, Any, List, Optional, Union
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.types import interrupt # interrupt 임포트
from pydantic import BaseModel, Field # Pydantic 모델 사용

from ...core.llm_provider import get_high_performance_llm
from ...models.why_graph_state import WhyGraphState # 타입 힌팅용

class AssumptionQuestionOutput(BaseModel):
    assumption_question: str = Field(
        ...,
        description=(
            "선택된 특정 가정에 대해 사용자의 근거, 확신도, 또는 반대 상황을 탐색하는 "
            "명확하고 개방적인 단 하나의 질문입니다."
        )
    )

async def probe_assumption_node(state: Dict[str, Any]) -> Union[Dict[str, Any], None]:
    """
    Probe Assumption 노드:
    식별된 가정 목록에서 아직 탐색하지 않은 가장 중요한 가정을 선택하여
    하나의 개방형 질문을 생성하고 interrupt를 발생시킵니다 (assumption_question을 상태에 포함).
    모든 가정이 탐색되었으면 상태 업데이트 딕셔너리를 반환합니다.
    """
    print("[PROBE][NODE_LIFECYCLE] Entering probe_assumption_node")

    # 현재 단계의 대화 기록만 사용
    current_probe_messages: List[Union[BaseMessage, dict]] = state.get('probe_messages', [])
    identified_assumptions: List[str] = state.get('identified_assumptions', [])
    current_probed_assumptions: List[str] = state.get('probed_assumptions', []) 
    idea_summary = state.get('idea_summary', 'N/A')
    motivation_summary = state.get('motivation_summary') or state.get('final_motivation_summary', 'N/A')

    # 메시지 이력 문자열화 (LLM 프롬프트용)
    history_lines_for_prompt = []
    current_messages_for_state = [] # BaseMessage 객체로 일관성 유지
    for i, msg_data in enumerate(current_probe_messages):
        role = None; content = None; msg_obj = None
        if isinstance(msg_data, HumanMessage): 
            role, content, msg_obj = "User", msg_data.content, msg_data
        elif isinstance(msg_data, AIMessage): 
            role, content, msg_obj = "Assistant", msg_data.content, msg_data
        elif isinstance(msg_data, dict):
            msg_type = msg_data.get("type")
            raw_content = msg_data.get("content")
            if msg_type == "human": 
                role, content = "User", raw_content
                if raw_content is not None: msg_obj = HumanMessage(content=raw_content, additional_kwargs=msg_data.get("additional_kwargs",{}))
            elif msg_type == "ai" or msg_type == "assistant": 
                role, content = "Assistant", raw_content
                if raw_content is not None: msg_obj = AIMessage(content=raw_content, additional_kwargs=msg_data.get("additional_kwargs",{}))
        
        if role and content is not None:
            history_lines_for_prompt.append(f"- {role}: {content}")
        if msg_obj: # BaseMessage 객체만 messages 리스트에 유지
            current_messages_for_state.append(msg_obj)
        elif isinstance(msg_data, dict) and msg_obj is None and content is not None : # 변환 실패했으나 내용은 있는 경우 dict 유지(주의)
            current_messages_for_state.append(msg_data)

    # 다음 탐색할 가정 선택
    assumption_to_probe: Optional[str] = None
    for assumption_str in identified_assumptions:
        if assumption_str not in current_probed_assumptions:
            assumption_to_probe = assumption_str
            break
    
    # 모든 가정 탐색 완료 시
    if assumption_to_probe is None:
        print("  [PROBE][DEBUG] All assumptions already probed. Setting flag and returning state.")
        return {
            'probe_messages': current_messages_for_state, # 현재 단계의 대화 기록
            'probed_assumptions': current_probed_assumptions,
            'assumptions_fully_probed': True,
            'assumption_question': None,
            'assumption_being_probed_now': None
        }

    print(f"  [PROBE][DEBUG] Assumption to probe: {assumption_to_probe}")

    # LLM 준비
    llm = get_high_performance_llm()
    structured_llm = llm.with_structured_output(AssumptionQuestionOutput)

    # 시스템 프롬프트 구성
    system_prompt = f"""
# 역할: 당신은 사용자의 아이디어와 동기를 바탕으로 식별된 특정 가정('{assumption_to_probe}')에 대해 사용자의 근거, 확신도, 또는 그 가정이 틀렸을 때의 잠재적 영향을 탐색하는 단 하나의 명확하고 개방적인 질문을 생성하는 전문가 질문자입니다.
# 입력 정보:
* **탐색 대상 가정:** {assumption_to_probe}
* **아이디어 요약:** {idea_summary}
* **동기 요약:** {motivation_summary}
* **전체 가정 목록 (중요도 순):**
- {'- '.join(identified_assumptions)}
* **대화 내용:** 아래 대화 내용을 참고하세요.
# 핵심 지침:
1. **가정 집중:** 선택된 가정('{assumption_to_probe}')에 대해서만 질문을 작성하세요.
2. **탐색 각도:** 근거('왜 그렇게 생각하시나요?'), 확신도('얼마나 확신하시나요?'), 영향('만약 틀리다면 어떤 일이 발생할까요?'), 또는 대안('다른 가능성은 없을까요?')을 탐색하는 질문 중 하나를 선택하세요. 이전 대화 흐름을 고려하여 가장 적절한 각도를 선택하세요.
3. **개방형 질문:** 사용자가 상세히 답변하도록 유도하는 질문을 하세요. 예/아니오로 답할 수 없도록 만드세요.
4. **단일 질문:** 가장 효과적이고 중요한 하나의 질문만 생성하세요.
5. **구조화된 출력:** JSON 형식(`{{"assumption_question": "..."}}`)으로 반환하세요.
""".strip()
    user_prompt_for_llm = (
        f"Identified Assumptions (Priority Order):\n- " + "\n- ".join(identified_assumptions) + "\n\n"
        f"Dialogue History:\n" + "\n".join(history_lines_for_prompt)
    )
    
    # LLM 호출
    try:
        print(f"  [PROBE][INFO] Calling LLM to generate question for assumption: {assumption_to_probe}")
        llm_output: AssumptionQuestionOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt_for_llm)
        ])
        ai_generated_question = llm_output.assumption_question
        print("  [PROBE][INFO] LLM call completed.")
        print(f"  [PROBE][DEBUG] Generated question: {ai_generated_question}")
    except Exception as e:
        print(f"  [PROBE][ERROR] LLM call failed: {e}")
        ai_generated_question = f"(시스템 오류: 가정 탐색 질문 생성 실패 - {e})"
        error_interrupt_data = {
            'probe_messages': current_messages_for_state + [AIMessage(content=ai_generated_question)],
            'probed_assumptions': current_probed_assumptions,
            'assumptions_fully_probed': False,
            'error_message': f"LLM Error in probe_assumption: {str(e)}",
            "assumption_question": ai_generated_question,
            "assumption_being_probed_now": assumption_to_probe 
        }
        print(f"[PROBE][NODE_LIFECYCLE] Exiting probe_assumption_node with interrupt (error): {ai_generated_question}")
        raise interrupt(ai_generated_question).with_data(error_interrupt_data)

    # 인터럽트 발생
    updated_messages_with_ai_q = current_messages_for_state + [AIMessage(content=ai_generated_question)]
    interrupt_data_for_probe = {
        'probe_messages': updated_messages_with_ai_q, # 현재 단계의 대화 기록만 유지
        'probed_assumptions': current_probed_assumptions,
        'assumptions_fully_probed': False,
        "assumption_question": ai_generated_question,
        "assumption_being_probed_now": assumption_to_probe
    }
    print(f"[PROBE][NODE_LIFECYCLE] Exiting probe_assumption_node with interrupt (question): {ai_generated_question}")
    raise interrupt(ai_generated_question).with_data(interrupt_data_for_probe)
