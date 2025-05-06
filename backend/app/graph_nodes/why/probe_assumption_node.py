# backend/app/graph_nodes/why/probe_assumption_node.py

from typing import Dict, Any, List, Optional, Union
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
# from langgraph.types import interrupt # Interrupt 사용 안 함
from pydantic import BaseModel, Field

from ...core.llm_provider import get_high_performance_llm
from ...models.why_graph_state import WhyGraphState

class AssumptionQuestionOutput(BaseModel):
    assumption_question: str = Field(
        ...,
        description=(
            "선택된 특정 가정에 대해 사용자의 근거, 확신도, 또는 반대 상황을 탐색하는 "
            "명확하고 개방적인 단 하나의 질문입니다."
        )
    )

async def probe_assumption_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Probe Assumption 노드:
    식별된 가정 목록에서 아직 탐색하지 않은 가장 중요한 가정을 선택하여
    하나의 개방형 질문을 생성하고, 사용자 입력을 기다리는 상태 딕셔너리를 반환합니다.
    """
    print("[PROBE][DEBUG] Entering probe_assumption_node")

    messages: List[Union[BaseMessage, dict]] = state.get('messages', [])
    
    # --- messages 리스트 처리 로직 (동일하게 적용) ---
    processed_messages_for_prompt = []
    history_lines_for_prompt = []
    print(f"  [PROBE][DEBUG] Building history from messages list (length {len(messages)}): {messages}")
    for i, msg_data in enumerate(messages): 
        role = None
        content = None
        msg_obj = None 

        if isinstance(msg_data, HumanMessage):
            role = "User"
            content = msg_data.content
            msg_obj = msg_data
        elif isinstance(msg_data, AIMessage):
            role = "Assistant"
            content = msg_data.content
            msg_obj = msg_data
        elif isinstance(msg_data, dict): 
            if msg_data.get("type") == "human":
                role = "User"
                content = msg_data.get("content")
                msg_obj = HumanMessage(content=content, additional_kwargs=msg_data.get("additional_kwargs", {})) 
            elif msg_data.get("type") == "ai":
                role = "Assistant"
                content = msg_data.get("content")
                msg_obj = AIMessage(content=content, additional_kwargs=msg_data.get("additional_kwargs", {})) 
        
        if role and content is not None:
            history_lines_for_prompt.append(f"- {role}: {content}")
            if msg_obj:
                 processed_messages_for_prompt.append(msg_obj)
            print(f"    [PROBE][DEBUG] Processed msg {i} for prompt.")
        else:
             print(f"    [PROBE][WARN] Skipped msg {i} (type: {type(msg_data)})")
    # ------------------------------------

    identified_assumptions: List[str] = state.get('identified_assumptions', [])
    probed_assumptions: List[str] = state.get('probed_assumptions', []) # Should be a list
    idea_summary = state.get('idea_summary', 'N/A')
    motivation_summary = state.get('motivation_summary') or state.get('final_motivation_summary', 'N/A')

    # 다음 탐색할 가정 선택
    assumption_to_probe: Optional[str] = None
    for a in identified_assumptions:
        # probed_assumptions가 list 이므로 in 사용 가능
        if a not in probed_assumptions:
            assumption_to_probe = a
            break

    # 모든 가정 탐색 완료 시
    if assumption_to_probe is None:
        print("[PROBE][DEBUG] All assumptions already probed. Setting flag.")
        # assumptions_fully_probed 플래그 설정하여 반환
        return {
            'messages': processed_messages_for_prompt, 
            'probed_assumptions': probed_assumptions, 
            'assumptions_fully_probed': True, 
            'assumption_question': None, # 질문 없음을 명시
        }

    print(f"[PROBE][DEBUG] Assumption to probe: {assumption_to_probe}")

    llm = get_high_performance_llm()
    structured_llm = llm.with_structured_output(AssumptionQuestionOutput)

    system_prompt = f"""
# 역할: 당신은 사용자의 아이디어와 동기를 바탕으로 식별된 특정 가정('{assumption_to_probe}')에 대해
# 사용자의 근거, 확신도, 또는 그 가정이 틀렸을 때의 잠재적 영향을 탐색하는
# 단 하나의 명확하고 개방적인 질문을 생성하는 전문가 질문자입니다.

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

    # Use the full dialogue history for context
    user_prompt = (
        f"Identified Assumptions (Priority Order):\n- " + "\n- ".join(identified_assumptions) + "\n\n"
        f"Dialogue History:\n" + "\n".join(history_lines_for_prompt) 
    )

    print(f"[PROBE][DEBUG] user_prompt for probing: {user_prompt}")

    try:
        print(f"[PROBE][INFO] Calling LLM to generate question for assumption: {assumption_to_probe}")
        output: AssumptionQuestionOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        ai_question = output.assumption_question
        # probed_assumptions 업데이트는 이 노드의 책임이 아님.
        # 오케스트레이터 또는 다음 턴 시작 시 사용자 답변과 함께 처리하는 것이 좋음.
        # 여기서는 probed_assumptions를 수정하지 않음.
        # updated_probed = probed_assumptions + [assumption_to_probe] # <--- 이 라인 제거 또는 주석 처리
        print("[PROBE][INFO] LLM call completed.")
        print(f"[PROBE][DEBUG] Generated question: {ai_question}")
    except Exception as e:
        print(f"[PROBE][ERROR] LLM call failed: {e}")
        import traceback
        traceback.print_exc()
        ai_question = f"(System Error: Failed to generate assumption question - {e})"
        # updated_probed = probed_assumptions # 오류 시에도 수정 안 함

    # --- Return state dictionary with assumption_question ---
    updated_messages = processed_messages_for_prompt + [AIMessage(content=ai_question)]
    return_state = {
        'messages': updated_messages,
        'probed_assumptions': probed_assumptions, # probed_assumptions는 아직 업데이트하지 않음
        'assumptions_fully_probed': False, 
        'assumption_question': ai_question # <--- 사용자 입력을 기다린다는 신호 키
        # 'assistant_message': ai_question # assistant_message는 messages[-1]로 대체 가능
    }
    print(f"[PROBE][DEBUG] Returning state: {return_state}")
    return return_state
    # ---------------------------------------------
