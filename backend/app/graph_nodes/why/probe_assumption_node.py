# backend/app/graph_nodes/why/probe_assumption_node.py

from typing import Dict, Any, List, Optional, Union
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.types import interrupt # interrupt 임포트
from pydantic import BaseModel, Field # Pydantic 모델 사용

from ...core.llm_provider import get_high_performance_llm
from ...models.why_graph_state import WhyGraphState # 타입 힌팅용

class AssumptionProbeOutput(BaseModel):
    is_fully_probed: bool = Field(..., description="가정이 충분히 탐구되었는지 여부")
    next_question: Optional[str] = Field(None, description="추가 탐구가 필요한 경우의 다음 질문")
    current_insights: str = Field(..., description="현재까지의 탐구 인사이트")

async def probe_assumption_node(state: Dict[str, Any]) -> Union[Dict[str, Any], None]:
    """
    Probe Assumption 노드:
    식별된 가정 목록에서 아직 탐색하지 않은 가장 중요한 가정을 선택하여
    충분한 탐구가 이루어질 때까지 대화를 이어나가고,
    완전히 탐구되었을 때 다음 가정으로 넘어갑니다.
    """
    print("[PROBE][NODE_LIFECYCLE] Entering probe_assumption_node")

    # 현재 단계의 대화 기록만 사용
    current_probe_messages: List[Union[BaseMessage, dict]] = state.get('probe_messages', [])
    identified_assumptions: List[str] = state.get('identified_assumptions', [])
    current_probed_assumptions: List[str] = state.get('probed_assumptions', []) 
    idea_summary = state.get('idea_summary', 'N/A')
    motivation_summary = state.get('motivation_summary') or state.get('final_motivation_summary', 'N/A')
    current_assumption = state.get('assumption_being_probed_now')

    # 메시지 이력 문자열화 (LLM 프롬프트용)
    history_lines_for_prompt = []
    current_messages_for_state = []
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
        if msg_obj: 
            current_messages_for_state.append(msg_obj)
        elif isinstance(msg_data, dict) and msg_obj is None and content is not None : 
            current_messages_for_state.append(msg_data)

    # 다음 탐색할 가정 선택
    assumption_to_probe: Optional[str] = None
    if not current_assumption:  # 현재 탐구 중인 가정이 없는 경우
        for assumption_str in identified_assumptions:
            if assumption_str not in current_probed_assumptions:
                assumption_to_probe = assumption_str
                break
    else:
        assumption_to_probe = current_assumption

    # 모든 가정 탐색 완료 시
    if assumption_to_probe is None:
        print("  [PROBE][DEBUG] All assumptions already probed. Setting flag and returning state.")
        return {
            'probe_messages': current_messages_for_state,
            'probed_assumptions': current_probed_assumptions,
            'assumptions_fully_probed': True,
            'assumption_question': None,
            'assumption_being_probed_now': None,
            'messages': state.get('messages', []) + current_messages_for_state,  # 전체 메시지 이력 업데이트
            'current_node': 'findings_summarization'  # 다음 노드로 이동
        }

    print(f"  [PROBE][DEBUG] Assumption to probe: {assumption_to_probe}")

    # LLM 준비
    llm = get_high_performance_llm()
    structured_llm = llm.with_structured_output(AssumptionProbeOutput)

    # 시스템 프롬프트 구성
    system_prompt = f"""
# 역할: 당신은 사용자의 아이디어와 동기를 바탕으로 식별된 특정 가정('{assumption_to_probe}')에 대해 깊이 있는 탐구를 진행하는 전문가입니다.

# 목표:
1. 현재 가정에 대한 탐구가 충분한지 평가
2. 추가 탐구가 필요한 경우 다음 질문 생성
3. 현재까지의 탐구 인사이트 정리

# 평가 기준:
1. 가정의 근거가 충분히 탐구되었는가?
2. 가정이 틀렸을 때의 영향이 충분히 논의되었는가?
3. 대안적 관점이 충분히 고려되었는가?
4. 사용자의 확신도가 명확해졌는가?

# 입력 정보:
* **탐색 대상 가정:** {assumption_to_probe}
* **아이디어 요약:** {idea_summary}
* **동기 요약:** {motivation_summary}
* **전체 가정 목록 (중요도 순):**
- {'- '.join(identified_assumptions)}
* **대화 내용:** 아래 대화 내용을 참고하세요.

# 응답 형식:
{{
    "is_fully_probed": true/false,
    "next_question": "추가 탐구가 필요한 경우의 질문",
    "current_insights": "현재까지의 탐구 인사이트"
}}
"""

    user_prompt = (
        f"Identified Assumptions (Priority Order):\n- " + "\n- ".join(identified_assumptions) + "\n\n"
        f"Dialogue History:\n" + "\n".join(history_lines_for_prompt)
    )
    
    # LLM 호출
    try:
        print(f"  [PROBE][INFO] Calling LLM to evaluate assumption probe status: {assumption_to_probe}")
        llm_output: AssumptionProbeOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        print("  [PROBE][INFO] LLM call completed.")
        print(f"  [PROBE][DEBUG] LLM output: {llm_output}")
    except Exception as e:
        print(f"  [PROBE][ERROR] LLM call failed: {e}")
        error_msg = f"(시스템 오류: 가정 탐구 상태 평가 실패 - {e})"
        error_interrupt_data = {
            'probe_messages': current_messages_for_state + [AIMessage(content=error_msg)],
            'probed_assumptions': current_probed_assumptions,
            'assumptions_fully_probed': False,
            'error_message': f"LLM Error in probe_assumption: {str(e)}",
            "assumption_question": error_msg,
            "assumption_being_probed_now": assumption_to_probe,
            'messages': state.get('messages', []) + current_messages_for_state + [AIMessage(content=error_msg)],  # 전체 메시지 이력 업데이트
            'current_node': 'probe_assumption'  # 현재 노드 유지
        }
        print(f"[PROBE][NODE_LIFECYCLE] Exiting probe_assumption_node with interrupt (error): {error_msg}")
        raise interrupt(error_msg).with_data(error_interrupt_data)

    # 현재 가정이 충분히 탐구되었는지 확인
    if llm_output.is_fully_probed:
        print(f"  [PROBE][DEBUG] Assumption fully probed. Moving to next assumption.")
        return {
            'probe_messages': current_messages_for_state,
            'probed_assumptions': current_probed_assumptions + [assumption_to_probe],
            'assumptions_fully_probed': False,  # 다음 가정이 있을 수 있으므로
            'assumption_being_probed_now': None,
            'current_assumption_insights': llm_output.current_insights,
            'messages': state.get('messages', []) + current_messages_for_state,  # 전체 메시지 이력 업데이트
            'current_node': 'probe_assumption'  # 다음 가정 탐구를 위해 현재 노드 유지
        }
    else:
        # 추가 탐구가 필요한 경우
        next_question = llm_output.next_question
        updated_messages_with_ai_q = current_messages_for_state + [AIMessage(content=next_question)]
        interrupt_data_for_probe = {
            'probe_messages': updated_messages_with_ai_q,
            'probed_assumptions': current_probed_assumptions,
            'assumptions_fully_probed': False,
            "assumption_question": next_question,
            "assumption_being_probed_now": assumption_to_probe,
            "current_assumption_insights": llm_output.current_insights,
            'messages': state.get('messages', []) + updated_messages_with_ai_q,  # 전체 메시지 이력 업데이트
            'current_node': 'probe_assumption'  # 현재 노드 유지
        }
        print(f"[PROBE][NODE_LIFECYCLE] Exiting probe_assumption_node with interrupt (question): {next_question}")
        raise interrupt(next_question).with_data(interrupt_data_for_probe)
