# backend/app/graph_nodes/why/identify_assumptions_node.py

from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from pydantic import BaseModel, Field

# LLM Provider 및 상태 모델 임포트
from ...core.llm_provider import get_high_performance_llm # 가정 식별 및 중요도 평가는 고성능 모델
# from ...models.why_graph_state import WhyGraphState # 실제 정의된 WhyGraphState 임포트 가정
from ...models.why_graph_state import WhyGraphState

# 구조화된 출력을 위한 Pydantic 모델 정의
# LLM이 중요도 순서로 정렬된 리스트를 반환하도록 유도할 것이므로, 모델 자체는 이전과 동일하게 유지
class IdentifiedAssumptionsOutput(BaseModel):
    """식별된 가정 목록 모델 (중요도 순으로 정렬됨)"""
    identified_assumptions: List[str] = Field(description="아이디어와 동기를 바탕으로 식별된 핵심적인 기저 가정들의 목록입니다. **가장 중요하거나 아이디어 성공에 치명적인 영향을 미치는 가정부터 순서대로 정렬되어야 합니다.**")
    # rationale: Optional[str] = Field(None, description="가정 식별 및 정렬 과정에 대한 간략한 설명 (내부 로깅/디버깅용)")

async def identify_assumptions_node(state: WhyGraphState) -> Dict[str, Any]:
    """
    Identify Assumptions 노드 (수정됨): 아이디어 요약과 명확해진 동기를 바탕으로
    핵심적인 기저 가정들을 식별하고 **중요도 순서로 정렬**하여 상태에 저장합니다.
    (수정됨: 입력 상태 확인 로직 우선 실행)
    """
    print("--- Identify Assumptions Node 실행 (Prioritized) ---")

    # --- 1. 상태 정보 읽기 및 필수 입력 확인 (LLM 로드 전) ---
    try:
        idea_summary = state.get('idea_summary')
        final_motivation_summary = state.get('final_motivation_summary')

        # *** 중요: 필수 입력값 확인을 먼저 수행 ***
        if not idea_summary or not final_motivation_summary:
            missing = []
            if not idea_summary: missing.append("idea_summary")
            if not final_motivation_summary: missing.append("final_motivation_summary")
            error_msg = f"IdentifyAssumptions: 상태에 필수 정보({', '.join(missing)})가 없습니다."
            print(error_msg)
            # 필수 입력 없으면 LLM 로드 없이 즉시 오류 반환
            return {"error_message": error_msg}

        # 참고용 메시지 기록 (선택적)
        messages = state.get('messages', [])

    except KeyError as e:
        print(f"IdentifyAssumptions: 상태 객체에서 필수 키 누락 - {e}")
        return {"error_message": f"IdentifyAssumptions 상태 객체 키 누락: {e}"}
    # --- ---

    # --- 2. LLM 클라이언트 가져오기 (입력 확인 후) ---
    try:
        llm_identifier = get_high_performance_llm() # 가정 식별 및 중요도 평가는 분석적 작업
        structured_llm = llm_identifier.with_structured_output(IdentifiedAssumptionsOutput)
    except Exception as e:
        print(f"IdentifyAssumptions: LLM 클라이언트 로드 실패 - {e}")
        # LLM 로드 실패 시 사용자에게 전달할 필요는 없을 수 있음 (내부 오류)
        return {"error_message": f"LLM 클라이언트 로드 실패: {e}"}
    # --- ---

    # --- 3. 시스템 프롬프트 구성 (이제 idea_summary, final_motivation_summary 존재 보장) ---
    system_prompt_text = f"""
# 역할: 당신은 사용자의 아이디어와 그 동기 이면에 숨어있는 **핵심적인 기저 가정(underlying assumptions)**을 식별하고 **그 중요도를 평가**하는 날카로운 분석가입니다. 당신의 목표는 명시적으로 언급되지 않았더라도 아이디어가 성공하거나 동기가 타당하기 위해 **암묵적으로 전제하고 있는 조건, 믿음, 또는 인과관계**를 찾아내고, **가장 중요하거나 아이디어에 치명적인 영향을 미치는 순서대로 정렬**하여 목록으로 반환하는 것입니다.

# 입력 정보:
* **사용자 아이디어 요약:** {idea_summary}
* **사용자의 핵심 동기 요약:** {final_motivation_summary}
* **(참고) 최근 대화 기록:** (필요시 messages 변수 활용)

# 핵심 지침:
1.  **심층 분석 및 가정 식별:** 제공된 아이디어 요약과 동기 요약을 면밀히 분석하여 숨겨진 핵심 전제들을 파악하세요. 다양한 유형(사용자, 시장, 기술, 자원, 인과관계, 가치 판단 등)의 가정을 고려하세요. 3~5개 정도의 가장 중요한 가정을 식별하는 것을 목표로 하세요.
2.  **중요도 평가:** 식별된 각 가정에 대해 **"이 가정이 만약 틀렸다면, 원래 아이디어나 목표 달성에 얼마나 심각한(또는 치명적인) 영향을 미치는가?"** 를 기준으로 중요도를 평가하세요.
3.  **중요도 순 정렬 (매우 중요):** 평가된 중요도를 바탕으로, **가장 중요하거나 치명적인 영향을 미치는 가정이 리스트의 맨 앞에 오도록** 식별된 가정 목록을 **내림차순으로 정렬**하세요.
4.  **명확한 문장 표현:** 각 가정은 독립적이고 명확한 문장으로 표현하세요.
5.  **구조화된 출력:** 반드시 지정된 JSON 형식(`{{"identified_assumptions": ["가장 중요한 가정...", "그 다음 중요한 가정...", ...]}}`)으로 **중요도 순서로 정렬된** 가정 목록을 출력하세요.

# 출력 지침: 위 역할과 지침에 따라, 제공된 아이디어와 동기를 바탕으로 식별 및 **중요도 순으로 정렬된** 핵심 가정 목록을 포함한 JSON 객체를 생성하세요. 정렬된 가정 목록만 출력하면 됩니다.
"""
    # --- ---

    # --- 4. LLM 호출 및 결과 처리 ---
    prompt_messages: List[BaseMessage] = [
        SystemMessage(content=system_prompt_text.strip())
    ]
    model_name_to_log = getattr(llm_identifier, 'model', getattr(llm_identifier, 'model_name', 'N/A'))
    print(f"IdentifyAssumptions: LLM 호출 준비 (Model: {model_name_to_log}, Structured Output: IdentifiedAssumptionsOutput, Prioritization Enabled)")

    try:
        response_object: IdentifiedAssumptionsOutput = await structured_llm.ainvoke(prompt_messages)
        # LLM이 중요도 순으로 정렬해서 반환했다고 가정
        prioritized_assumptions_list = response_object.identified_assumptions
        print(f"IdentifyAssumptions: LLM 응답 수신 (구조화됨) - {len(prioritized_assumptions_list)}개 가정 식별 및 정렬됨.")
        error_message_to_return = None # 성공

        if not prioritized_assumptions_list:
            print("IdentifyAssumptions: 식별된 가정이 없습니다.")
            # 가정이 없는 경우도 정상 처리

    except Exception as e:
        # LLM 호출 오류 처리
        error_msg = f"IdentifyAssumptions: LLM 호출 오류 - {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        # 상태에 오류 기록
        return { "error_message": error_msg } # messages 업데이트는 필요 없음

    # --- ---

    # --- 5. 상태 업데이트 준비 및 반환 ---
    updates_to_state = {
        # 중요도 순으로 정렬된 가정 목록을 상태에 저장
        "identified_assumptions": prioritized_assumptions_list if 'prioritized_assumptions_list' in locals() else [],
        "probed_assumptions": [], # 다음 단계 위해 초기화
        "error_message": error_message_to_return, # 성공 시 None
    }
    print(f"IdentifyAssumptions: 상태 업데이트 반환 - Identified Assumptions: {updates_to_state['identified_assumptions']}")
    # --- ---

    return updates_to_state