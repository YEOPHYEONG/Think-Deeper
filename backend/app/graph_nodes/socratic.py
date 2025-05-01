# backend/app/graph_nodes/socratic.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from pydantic import BaseModel, Field # --- 구조화된 출력을 위해 추가 ---

# --- LLM Provider 및 상태 모델 임포트 ---
# Socratic 질문은 때로 복잡한 맥락 이해가 필요할 수 있으므로 high_perf 사용 고려
from ..core.llm_provider import get_high_performance_llm, get_fast_llm
from ..models.graph_state import GraphState

# --- 구조화된 출력을 위한 Pydantic 모델 정의 ---
class SocraticOutput(BaseModel):
    """Socratic 에이전트의 구조화된 출력 모델"""
    socratic_question: str = Field(description="사용자의 자기 발견을 촉진하기 위한 가장 적절한 단 하나의 소크라테스식 질문입니다.")
    question_type: str = Field(description="질문의 의도/유형입니다 (예: '가정 탐색', '결과 탐색', '개념 명확화' 등)")

# --- Socratic 노드 함수 정의 ---
async def socratic_node(state: GraphState) -> Dict[str, Any]:
    """
    Socratic 에이전트 노드. 사용자가 스스로 생각하고 답을 발견하도록
    소크라테스식 질문을 통해 안내합니다. (LLM Provider 및 구조화된 출력 사용)
    """
    print("--- Socratic Node 실행 ---")

    # --- 필요한 LLM 클라이언트 가져오기 ---
    try:
        # Socratic 질문은 맥락 이해가 중요할 수 있으므로 high_perf 사용
        llm_socratic = get_high_performance_llm()
        structured_llm = llm_socratic.with_structured_output(SocraticOutput)
    except Exception as e:
        print(f"Socratic: LLM 클라이언트 로드 실패 - {e}")
        return {"error_message": f"LLM 클라이언트 로드 실패: {e}"}

    # --- 상태 정보 읽기 ---
    try:
        messages = state['messages']
        current_focus = state.get("current_focus")
        if not messages:
             return {"error_message": "Socratic 입력 메시지가 비어있습니다."}
        # 마지막 사용자 메시지를 주요 분석 대상으로 삼음
        last_user_message_content = messages[-1].content if isinstance(messages[-1], HumanMessage) else None
        if not last_user_message_content:
             print("Socratic: 마지막 메시지가 사용자 입력이 아님. 이전 기록 참조.")
             # TODO: 더 나은 대상 메시지 선정 로직 필요
             pass

    except KeyError as e:
        print(f"Socratic: 상태 객체에서 필수 키 누락 - {e}")
        return {"error_message": f"Socratic 상태 객체 키 누락: {e}"}

    # --- 시스템 프롬프트 구성 (제공된 예시 기반) ---
    system_prompt_text = f"""
# 역할: 당신은 소크라테스식 대화법을 사용하여 사용자가 **스스로 생각하고 답을 발견하도록 안내**하는 AI 조력자(Socratic)입니다. 당신의 목표는 직접적인 답변, 비판, 또는 옹호를 제공하는 대신, **개방형 질문**을 통해 사용자의 **이해를 심화**시키고, **가정을 검토**하게 하며, **논리적 추론을 촉진**하여 **스스로 개선된 결론**에 도달하도록 돕는 것입니다. 당신은 사용자의 사고 여정을 촉진하는 가이드입니다.

# 핵심 지침:
1. **사용자 주도 학습 촉진:** 당신의 질문은 사용자가 자신의 아이디어를 명확히 하고, 다양한 각도에서 검토하며, 스스로 통찰력을 얻도록 설계되어야 합니다. 답을 제시하지 마세요.
2. **소크라테스식 질문 패턴 활용:** 사용자의 마지막 발언과 현재 맥락(`{{current_focus}}`)을 바탕으로 다음 질문 유형 중 **가장 적절한 하나**를 선택하여 사용하세요: 개념 명확화, 가정 탐색, 근거/증거 탐색, 결과/함의 탐색, 대안적 관점 탐색.
3. **개방형 질문 유지:** 사용자가 자신의 생각을 설명하도록 유도하는 질문을 하세요.
4. **능동적 경청 및 연결:** 사용자의 이전 답변 내용을 **반영**하거나 **연결**하여 다음 질문을 구성하세요.
5. **중립성 유지:** 사용자의 의견에 동의하거나 반대하는 대신, 질문을 통해 스스로 장단점을 평가하도록 유도하세요. Why 에이전트와 달리, 사용자 탐색 과정을 돕는 데 집중하세요.
6. **핵심 집중 응답 (매우 중요):** **매 턴마다 사용자의 현재 이해 수준과 논의 지점에서 가장 유익하다고 판단되는 단 하나의 소크라테스식 질문에만 집중하세요.**
7. **구조화된 출력:** 반드시 지정된 JSON 형식({{"socratic_question": "...", "question_type": "..."}})으로 출력해야 합니다.
8. **어조:** 호기심 있고, 존중하며, 인내심 있는 **조력자(facilitator)**의 어조를 유지하세요.

# 입력 컨텍스트 활용:
* 사용자의 마지막 메시지(`{{messages[-1].content}}`)를 분석하여 다음 질문의 출발점으로 삼으세요.
* 현재 논의 초점(`{{current_focus}}`)을 고려하여 대화의 전체적인 목표와 관련된 질문을 하세요.

# Few-Shot 예제 가이드:
* (여기에 적절한 질문 유형 선택, 개방형 질문 제시, 중립적/촉진적 어조, JSON 형식을 지키는 예시들을 삽입합니다.)
* 예시1 (가정 탐색):
    * 입력 컨텍스트: 사용자 "모든 직원은 주 4일 근무해야 생산성이 오른다."
    * 당신의 출력 (JSON): {{"socratic_question": "모든 직원이 동일한 근무 형태에서 최상의 생산성을 발휘한다고 가정하시는 특별한 이유가 있으신가요? 혹시 직무 특성이나 개인 선호도에 따라 다른 결과가 나올 가능성은 없을까요?", "question_type": "가정 탐색"}}
* 예시2 (결과 탐색):
    * 입력 컨텍스트: 사용자 "신기술 X를 즉시 도입해야 한다."
    * 당신의 출력 (JSON): {{"socratic_question": "신기술 X를 즉시 도입했을 때, 우리 팀의 현재 워크플로우나 기존 시스템과의 호환성 측면에서 예상되는 긍정적, 그리고 혹시 부정적인 영향은 무엇일지 좀 더 자세히 생각해 볼 수 있을까요?", "question_type": "결과 탐색"}}

# 출력 지침: 위 역할과 지침, 예제를 엄격히 따라서, 현재 대화 맥락에 가장 적합한 단일 소크라테스식 질문과 그 유형을 담은 JSON 객체를 생성하세요.
"""

    # --- LLM 입력 메시지 생성 ---
    # TODO: 컨텍스트 관리 개선 필요
    prompt_messages: List[BaseMessage] = [SystemMessage(content=system_prompt_text.strip())]
    prompt_messages.extend(messages[-5:]) # 예시: 최근 5개 메시지 (조절 필요)

    # --- LLM 호출 (구조화된 출력 사용) ---
    model_name_to_log = getattr(llm_socratic, 'model', getattr(llm_socratic, 'model_name', 'N/A'))
    print(f"Socratic: LLM 호출 준비 (Model: {model_name_to_log}, Structured Output: SocraticOutput)")

    try:
        response_object: SocraticOutput = await structured_llm.ainvoke(prompt_messages)
        print(f"Socratic: LLM 응답 수신 (구조화됨) - Question: {response_object.socratic_question[:50]}...")

        # 사용자에게 전달할 최종 응답 문자열 생성 (질문만 전달)
        final_response_string = response_object.socratic_question

    except Exception as e:
        error_msg = f"Socratic: LLM 호출 오류 - {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            "error_message": error_msg,
            "messages": [AIMessage(content=f"(시스템 오류: Socratic 응답 생성 실패 - {e})")]
        }

    # --- 상태 업데이트 준비 ---
    updates_to_state = {
        "messages": [AIMessage(content=final_response_string)], # 생성된 질문을 메시지에 추가
        "last_socratic_output": response_object.dict(), # 구조화된 결과 저장 (선택 사항)
        # Socratic 질문은 보통 현재 포커스를 유지하거나 사용자가 정의하게 함
        # "current_focus": ..., # 필요시 업데이트
        "error_message": None,
    }
    print(f"Socratic: 상태 업데이트 반환 - { {k: v for k, v in updates_to_state.items() if k != 'messages'} }")

    return updates_to_state