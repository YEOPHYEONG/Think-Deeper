# backend/app/graph_nodes/why/clarify_motivation_node.py

from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from pydantic import BaseModel, Field

# LLM Provider 및 상태 모델 임포트
from ...core.llm_provider import get_high_performance_llm # 심층 분석 및 질문 생성
from ...models.why_graph_state import WhyGraphState
# 구조화된 출력을 위한 Pydantic 모델 정의
class MotivationClarityOutput(BaseModel):
    """동기 명확성 판단 및 후속 질문 생성 모델"""
    is_motivation_clear: bool = Field(description="사용자의 답변을 분석했을 때, 아이디어의 핵심 동기('Why')가 다음 단계(가정 탐색)로 넘어갈 만큼 충분히 명확하게 설명되었는지 여부 (True/False)")
    clarification_question: Optional[str] = Field(None, description="만약 동기가 아직 불명확하다면(is_motivation_clear=False), 더 깊은 이해를 위해 사용자에게 던질 구체적이고 통찰력 있는 단 하나의 추가 질문입니다.")
    summary_of_motivation: Optional[str] = Field(None, description="만약 동기가 명확하다면(is_motivation_clear=True), 다음 단계를 위해 파악된 핵심 동기를 간결하게 요약한 문장입니다.")
    # rationale: Optional[str] = Field(None, description="명확성 판단 또는 질문 생성의 근거 (내부 로깅/디버깅용)")

async def clarify_motivation_node(state: WhyGraphState) -> Dict[str, Any]:
    """
    Clarify Motivation 노드: 사용자의 동기 답변을 분석하여 명확성을 판단하고,
    불명확하면 추가 질문을 생성하거나, 명확하면 동기 요약을 상태에 저장합니다.
    """
    print("--- Clarify Motivation Node 실행 ---")

    # LLM 클라이언트 가져오기
    try:
        llm_analyzer = get_high_performance_llm() # 명확성 판단 및 질문 생성 위해 고성능 모델
        structured_llm = llm_analyzer.with_structured_output(MotivationClarityOutput)
    except Exception as e:
        print(f"ClarifyMotivation: LLM 클라이언트 로드 실패 - {e}")
        return {"error_message": f"LLM 클라이언트 로드 실패: {e}"}

    # 상태 정보 읽기 (무조건 LLM 호출하도록 단순화)
    messages = state.get("messages", [])
    idea_summary = state.get("idea_summary")

    # 이전 AI 질문과 사용자 답변을 가장 최근 것으로 선택
    ai_question_context = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            ai_question_context = msg.content
            break
    user_answer = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_answer = msg.content
            break
    ai_question_context = ai_question_context or "이전 질문 없음"
    user_answer = user_answer or ""


    # 시스템 프롬프트 구성
    system_prompt_text = f"""
# 역할: 당신은 사용자의 동기 설명을 분석하고 명확성을 판단하는 AI 분석가이자 질문자입니다. 목표는 사용자가 자신의 핵심 동기('Why')를 충분히 깊고 명확하게 이해했는지 평가하고, 그렇지 않다면 더 깊은 성찰을 유도하는 추가 질문을 던지는 것입니다.

# 입력 정보:
* **사용자의 아이디어 요약:** {idea_summary}
* **AI의 이전 질문:** {ai_question_context}
* **사용자의 답변:** {user_answer}

# 핵심 지침:
1.  **명확성 평가:** 사용자의 답변이 아이디어의 근본적인 'Why'(궁극적 목적, 핵심 가치, 해결하려는 진짜 문제 등)를 구체적이고 설득력 있게 설명하는지 평가하세요. 피상적이거나 모호한 답변은 '불명확'으로 판단합니다.
2.  **판단 기준:**
    * **명확 (Clear - is_motivation_clear=True):** 사용자가 자신의 핵심 동기를 구체적인 용어로 설명하고, 그것이 왜 중요한지에 대한 논리적인 이유를 제시하며, 아이디어와의 연결성이 분명합니다. 다음 단계(가정 탐색)로 넘어가도 좋습니다.
    * **불명확 (Unclear - is_motivation_clear=False):** 답변이 추상적이거나, 동문서답이거나, 여러 동기가 혼재되어 핵심을 파악하기 어렵거나, 논리적 근거가 부족합니다. 추가 질문이 필요합니다.
3.  **추가 질문 생성 (불명확 시):** 만약 동기가 불명확하다면, 사용자의 답변 내용 중 **가장 불명확하거나 더 깊이 탐색해야 할 부분**을 정확히 짚어내는 **단 하나의 구체적이고 통찰력 있는 후속 질문**을 생성하세요. 막연히 "더 자세히 설명해주세요"라고 하지 마세요. (예: "말씀하신 '성장'이 구체적으로 어떤 종류의 성장을 의미하는지 더 설명해주실 수 있나요?", "그 목표가 아이디어의 [특정 측면]과 어떻게 직접적으로 연결되는지 궁금합니다.")
4.  **동기 요약 생성 (명확 시):** 만약 동기가 명확하다면, 파악된 핵심 동기를 **다음 단계를 위해 간결하게 요약**하여 `summary_of_motivation` 필드에 담으세요.
5.  **구조화된 출력:** 반드시 지정된 JSON 형식(`{{"is_motivation_clear": boolean, "clarification_question": string | null, "summary_of_motivation": string | null}}`)으로 결과를 출력하세요.

# 출력 지침: 위 역할과 지침에 따라 사용자의 답변을 분석하여 명확성 여부를 판단하고, 필요한 경우 추가 질문을, 명확한 경우 동기 요약을 포함한 JSON 객체를 생성하세요.
"""

    # LLM 입력 메시지 생성 (시스템 프롬프트만으로 충분할 수 있음)
    prompt_messages: List[BaseMessage] = [
        SystemMessage(content=system_prompt_text.strip())
    ]
    # 필요시 이전 대화 일부를 추가하여 맥락 제공 가능
    # prompt_messages.extend(messages[-3:]) # 예: AI질문 + 사용자답변 + (그 이전 메시지)

    # LLM 호출
    model_name_to_log = getattr(llm_analyzer, 'model', getattr(llm_analyzer, 'model_name', 'N/A'))
    print(f"ClarifyMotivation: LLM 호출 준비 (Model: {model_name_to_log}, Structured Output: MotivationClarityOutput)")

    try:
        response_object: MotivationClarityOutput = await structured_llm.ainvoke(prompt_messages)
        print(f"ClarifyMotivation: LLM 응답 수신 (구조화됨) - Is Clear: {response_object.is_motivation_clear}")

        ai_message_content: Optional[str] = None
        updates_to_state: Dict[str, Any] = { "error_message": None }

        if response_object.is_motivation_clear:
            # 동기가 명확 -> 상태 업데이트 (다음 단계로 넘어갈 준비)
            updates_to_state["motivation_clear"] = True # 상태 모델에 이 필드가 있다고 가정
            updates_to_state["final_motivation_summary"] = response_object.summary_of_motivation # 상태 모델에 저장
            print(f"ClarifyMotivation: 동기 명확함. 요약: {response_object.summary_of_motivation}")
            # 이 경우 사용자에게 추가 질문을 보내지 않음
        else:
            # 동기가 불명확 -> 추가 질문 생성 및 메시지에 추가
            updates_to_state["motivation_clear"] = False
            if response_object.clarification_question:
                ai_message_content = response_object.clarification_question
                updates_to_state["messages"] = [AIMessage(content=ai_message_content)]
                print(f"ClarifyMotivation: 동기 불명확. 추가 질문 생성: {ai_message_content[:50]}...")
            else:
                # LLM이 질문 생성에 실패한 경우 처리
                print("ClarifyMotivation: 동기 불명확 판단했으나 추가 질문 생성 실패.")
                updates_to_state["error_message"] = "동기 명확화 질문 생성 실패"
                updates_to_state["messages"] = [AIMessage(content="(시스템 오류: 동기 명확화 질문 생성 실패. 다시 답변해주시겠어요?)")]

    except Exception as e:
        error_msg = f"ClarifyMotivation: LLM 호출 오류 - {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        updates_to_state = {
             "error_message": error_msg,
             "messages": [AIMessage(content=f"(시스템 오류: 동기 명확화 처리 실패 - {e})")]
        }

    # 상태 업데이트 반환
    print(f"ClarifyMotivation: 상태 업데이트 반환 - { {k: v for k, v in updates_to_state.items() if k != 'messages'} }")
    return updates_to_state