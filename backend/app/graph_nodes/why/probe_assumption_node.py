from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage
from langchain_core.pydantic_v1 import BaseModel, Field

# LLM Provider 및 상태 모델 임포트
from ...core.llm_provider import get_high_performance_llm
from ...models.why_graph_state import WhyGraphState

# 구조화된 출력을 위한 Pydantic 모델 정의
class AssumptionQuestionOutput(BaseModel):
    """가정 탐색 질문 생성 모델"""
    assumption_question: str = Field(
        description="선택된 특정 가정에 대해 사용자의 근거, 확신도, 또는 반대 상황을 탐색하는 명확하고 개방적인 단 하나의 질문입니다."
    )

async def probe_assumption_node(state: WhyGraphState) -> Dict[str, Any]:
    """
    Probe Assumption 노드: 정렬된 가정 목록에서 아직 탐색하지 않은
    가장 중요한 가정을 선택하여 질문하고, 탐색된 가정을 기록하며,
    일관된 키만 반환합니다.
    """
    print("--- Probe Assumption Node 실행 (Prioritized & Consistent Returns) ---")

    identified_assumptions = state.get('identified_assumptions', [])
    probed_assumptions = state.get('probed_assumptions', [])
    current_messages = state.get('messages', [])

    # 입력 유효성 검사
    if not isinstance(identified_assumptions, list):
        return {
            "probed_assumptions": probed_assumptions,
            "assumptions_fully_probed": False,
            "error_message": "ProbeAssumption: 'identified_assumptions' 상태가 리스트가 아닙니다."
        }
    if not isinstance(probed_assumptions, list):
        probed_assumptions = []

    # 다음 탐색할 가정 찾기
    assumption_to_probe: Optional[str] = None
    for assumption in identified_assumptions:
        if assumption not in probed_assumptions:
            assumption_to_probe = assumption
            break

    # 모든 가정 탐색 완료 시
    if assumption_to_probe is None:
        return {
            "probed_assumptions": probed_assumptions,
            "assumptions_fully_probed": True,
            "error_message": None
        }

    # LLM 호출 준비
    try:
        llm_questioner = get_high_performance_llm()
        structured_llm = llm_questioner.with_structured_output(AssumptionQuestionOutput)
    except Exception as e:
        error_msg = f"LLM 클라이언트 로드 실패: {e}"
        return {
            "messages": current_messages + [AIMessage(content=f"(시스템 오류: 질문 생성 준비 실패 - {e})")],
            "probed_assumptions": probed_assumptions,
            "assumptions_fully_probed": False,
            "error_message": error_msg
        }

    # 시스템 프롬프트 구성
    system_prompt_text = f"""
# 역할: 당신은 사용자가 자신의 아이디어나 동기의 기반이 되는 특정 **가정**에 대해 깊이 생각하도록 유도하는 질문자입니다. 당신의 목표는 제시된 가정에 대해 사용자가 어떤 근거를 가지고 있는지, 얼마나 확신하는지, 또는 그 가정이 틀렸을 경우 어떤 결과가 발생할지 등을 탐색하는 **단 하나의 명확하고 개방적인 질문**을 던지는 것입니다.

# 입력 정보:
* **현재 탐색할 가정:** {assumption_to_probe}
* **(참고) 사용자 아이디어 요약:** {state.get('idea_summary') or '제공되지 않음'}
* **(참고) 사용자의 핵심 동기 요약:** {state.get('final_motivation_summary') or '제공되지 않음'}

# 핵심 지침:
1.  **가정 집중:** 현재 탐색할 특정 가정(`{assumption_to_probe}`)에 대해서만 질문하세요.
2.  **탐색 각도:** 다음 중 하나의 각도에서 질문을 설계하세요: 근거 탐색, 확신도 탐색, 영향 탐색, 대안 탐색.
3.  **개방형 질문:** 사용자가 자신의 생각을 자세히 설명하도록 유도하세요.
4.  **명확성:** 질문이 명확하고 이해하기 쉬워야 합니다.
5.  **단일 질문:** **가장 중요하다고 생각되는 단 하나의 가정 탐색 질문**만 생성하세요.
6.  **구조화된 출력:** 반드시 지정된 JSON 형식(`{{"assumption_question": "..."}}`)으로 질문을 출력하세요.

# 출력 지침: 위 역할과 지침에 따라, 제시된 특정 가정에 대해 사용자의 생각을 탐색하는 가장 적절한 단일 질문을 JSON 객체로 생성하세요.
""".strip()
    prompt_messages: List[BaseMessage] = [SystemMessage(content=system_prompt_text)]

    # 질문 생성
    try:
        response_object: AssumptionQuestionOutput = await structured_llm.ainvoke(prompt_messages)
        ai_question_content = response_object.assumption_question
        updated_probed_assumptions = probed_assumptions + [assumption_to_probe]
        return {
            "messages": [AIMessage(content=ai_question_content)],
            "probed_assumptions": updated_probed_assumptions,
            "assumptions_fully_probed": False,
            "error_message": None
        }
    except Exception as e:
        error_msg = f"ProbeAssumption: LLM 호출 오류 - {e}"
        return {
            "messages": [AIMessage(content=f"(시스템 오류: 가정 탐색 질문 생성에 실패했습니다. - {e})")],
            "probed_assumptions": probed_assumptions,
            "assumptions_fully_probed": False,
            "error_message": error_msg
        }
