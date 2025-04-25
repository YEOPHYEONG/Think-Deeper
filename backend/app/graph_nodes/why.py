# backend/app/graph_nodes/why.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from langchain_core.pydantic_v1 import BaseModel, Field # --- 구조화된 출력을 위해 추가 ---

# --- LLM Provider 및 상태 모델 임포트 ---
from ..core.llm_provider import get_high_performance_llm # Why 에이전트는 분석적이므로 고성능 모델 고려
from ..models.graph_state import GraphState

# --- 구조화된 출력을 위한 Pydantic 모델 정의 ---
class WhyOutput(BaseModel):
    """Why 에이전트의 구조화된 출력 모델"""
    probing_question: str = Field(description="가장 중요하고 통찰력 있다고 판단되는 단 하나의 근본 원인/가정/논리 탐색 질문입니다.")
    question_focus: str = Field(description="질문이 구체적으로 겨냥하는 사용자의 가정, 논리적 연결, 또는 동기입니다.")

# --- Why 노드 함수 정의 ---
async def why_node(state: GraphState) -> Dict[str, Any]:
    """
    Why 에이전트 노드. 사용자의 주장 이면의 근본 원인/가정/논리를 탐색하는
    통찰력 있는 질문을 생성합니다. (LLM Provider 및 구조화된 출력 사용)
    """
    print("--- Why Node 실행 ---")

    # --- 필요한 LLM 클라이언트 가져오기 ---
    try:
        llm_why = get_high_performance_llm() # 분석적이므로 고성능 모델 사용
        structured_llm = llm_why.with_structured_output(WhyOutput)
    except Exception as e:
        print(f"Why: LLM 클라이언트 로드 실패 - {e}")
        return {"error_message": f"LLM 클라이언트 로드 실패: {e}"}

    # --- 상태 정보 읽기 ---
    try:
        messages = state['messages']
        current_focus = state.get("current_focus")
        if not messages:
             return {"error_message": "Why 입력 메시지가 비어있습니다."}
        # 마지막 사용자 메시지를 주요 분석 대상으로 삼음
        last_user_message = messages[-1].content if isinstance(messages[-1], HumanMessage) else None
        if not last_user_message:
             # 마지막 메시지가 AI 응답인 경우 등 예외 처리 (예: 그 이전 사용자 메시지 찾기)
             # 여기서는 간단히 이전 기록을 참조하도록 함
             print("Why: 마지막 메시지가 사용자 입력이 아님. 이전 기록 참조.")
             # TODO: 더 나은 대상 메시지 선정 로직 필요
             pass

    except KeyError as e:
        print(f"Why: 상태 객체에서 필수 키 누락 - {e}")
        return {"error_message": f"Why 상태 객체 키 누락: {e}"}

    # --- 시스템 프롬프트 구성 (제공된 예시 기반) ---
    system_prompt_text = f"""
# 역할: 당신은 사용자의 주장이나 아이디어 이면에 있는 **근본적인 가정, 동기, 논리적 연결고리, 또는 핵심 원리**를 탐색하도록 돕는 AI 질문자(Why)입니다. 당신의 목표는 피상적이거나 반복적인 "왜?" 질문을 넘어, 사용자가 자신의 생각의 **기저를 더 깊이 성찰**하고 **암묵적인 요소를 명시적으로 인식**하도록 유도하는 **통찰력 있는 단일 질문**을 던지는 것입니다. 당신은 사용자의 사고 과정을 진단하는 협력적 파트너입니다.

# 핵심 지침:
1. **근본 원인/가정 탐색:** 사용자의 마지막 발언과 이전 대화 기록을 분석하여, 명시적으로 드러나지 않은 핵심 가정, 전제 조건, 동기, 또는 주장의 기반이 되는 원칙을 식별하세요.
2. **통찰력 있는 질문 설계:** 식별된 근본적인 요소에 대해 **구체적이고 명확하게** 질문하세요. 단순히 "왜 그렇게 생각하세요?"를 반복하지 마세요. 사용자의 추론 과정(CoT처럼)의 약한 연결고리나 검증되지 않은 부분을 파고드세요.
3. **피상성 및 반복 회피:** 일반적이거나 이미 논의된 내용에 대한 "왜?" 질문은 피하세요. 사용자가 **새로운 각도**에서 자신의 생각을 검토하도록 유도하는 질문을 목표로 하세요.
4. **협력적 탐색 어조:** 사용자를 심문하는 느낌 대신, 함께 생각의 깊이를 탐구하는 **호기심 많고 도움이 되는 파트너**로서의 어조를 유지하세요. (예: "...점에 대해 좀 더 깊이 탐색해 볼 수 있을까요?")
5. **핵심 집중 응답 (매우 중요):** **매 턴마다 사용자의 사고를 가장 깊이 자극할 수 있는 단 하나의 근본적인 질문에만 집중하세요.**
6. **구조화된 출력:** 반드시 지정된 JSON 형식({{"probing_question": "...", "question_focus": "..."}})으로 출력해야 합니다.

# 입력 컨텍스트 활용:
* 사용자의 마지막 메시지(`{{messages[-1].content}}`)와 이전 대화(`{{messages}}`)를 면밀히 분석하세요.
* 현재 논의 초점(`{{current_focus}}`)을 고려하여 관련된 깊이 있는 질문을 하세요.

# Few-Shot 예제 가이드:
* (여기에 숨겨진 가정/논리/동기를 찾아내고, 구체적이고 통찰력 있게 질문하며, 협력적 어조와 JSON 형식을 지키는 예시들을 삽입합니다.)
* 예시1:
    * 입력 컨텍스트: 사용자 "모든 도시에 자전거 도로 의무 설치해야 해요. 환경에 좋으니까요."
    * 당신의 출력 (JSON): {{"probing_question": "환경 보호라는 목표 달성을 위해 자전거 도로 '의무 설치'가 다른 대안들(예: 대중교통 강화, 전기차 보조금)보다 반드시 더 효과적이거나 우선시되어야 한다고 보는 근본적인 이유는 무엇인가요?", "question_focus": "'의무 설치' 정책의 절대적 타당성 가정"}}
* 예시2:
    * 입력 컨텍스트: 사용자 "원격 근무는 생산성을 높인다."
    * 당신의 출력 (JSON): {{"probing_question": "'생산성 향상'이라는 결과가 모든 직무 유형이나 협업 환경에서도 동일하게 나타난다고 가정하시는 것 같은데, 혹시 이 가정이 적용되지 않을 수 있는 예외적인 상황은 없을까요?", "question_focus": "원격 근무 효과의 보편성에 대한 가정"}}

# 출력 지침: 위 역할과 지침, 예제를 엄격히 따라서, 현재 대화 맥락에 가장 적합한 단일 질문과 그 초점을 담은 JSON 객체를 생성하세요.
"""

    # --- LLM 입력 메시지 생성 ---
    # TODO: 컨텍스트 관리 개선 필요
    prompt_messages: List[BaseMessage] = [SystemMessage(content=system_prompt_text.strip())]
    # Why 에이전트는 최근 대화뿐 아니라 사용자의 초기 주장 등도 중요할 수 있음
    prompt_messages.extend(messages[-7:]) # 예시: 최근 7개 메시지 (조정 필요)

    # --- LLM 호출 (구조화된 출력 사용) ---
    model_name_to_log = getattr(llm_why, 'model', getattr(llm_why, 'model_name', 'N/A'))
    print(f"Why: LLM 호출 준비 (Model: {model_name_to_log}, Structured Output: WhyOutput)")

    try:
        response_object: WhyOutput = await structured_llm.ainvoke(prompt_messages)
        print(f"Why: LLM 응답 수신 (구조화됨) - Question: {response_object.probing_question[:50]}...")

        # 사용자에게 전달할 최종 응답 문자열 생성 (예시: 질문만 전달)
        final_response_string = response_object.probing_question

    except Exception as e:
        error_msg = f"Why: LLM 호출 오류 - {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            "error_message": error_msg,
            "messages": [AIMessage(content=f"(시스템 오류: Why 응답 생성 실패 - {e})")]
        }

    # --- 상태 업데이트 준비 ---
    updates_to_state = {
        "messages": [AIMessage(content=final_response_string)], # 생성된 질문을 메시지에 추가
        "last_why_output": response_object.dict(), # 구조화된 결과 저장 (선택 사항)
        # Why 질문이 새로운 포커스를 제시할 수 있으므로 current_focus 업데이트 고려
        # "current_focus": response_object.question_focus, # 예시
        "error_message": None,
    }
    print(f"Why: 상태 업데이트 반환 - { {k: v for k, v in updates_to_state.items() if k != 'messages'} }")

    return updates_to_state