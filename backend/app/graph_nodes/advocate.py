# backend/app/graph_nodes/advocate.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from langchain_core.pydantic_v1 import BaseModel, Field # --- 구조화된 출력을 위해 추가 ---

from ..core.llm_provider import get_high_performance_llm # Provider 함수 임포트
from ..models.graph_state import GraphState # 상태 모델 임포트

# --- 구조화된 출력을 위한 Pydantic 모델 정의 ---
class AdvocateOutput(BaseModel):
    """Advocate 에이전트의 구조화된 출력 모델"""
    advocacy_point: str = Field(description="가장 중요하다고 판단되는 단 하나의 핵심 옹호 내용 또는 강점입니다. 구체적으로 작성하세요.")
    brief_elaboration: str = Field(description="해당 옹호 포인트를 뒷받침하는 1-2 문장의 간결한 부연 설명, 근거 제시, 또는 Critic 의견에 대한 건설적 재구성입니다.")

# --- Advocate 노드 함수 정의 ---
async def advocate_node(state: GraphState) -> Dict[str, Any]:
    """
    Advocate 에이전트 노드. 사용자의 아이디어를 건설적으로 옹호합니다.
    (LLM Provider 및 구조화된 출력 사용)
    """
    print("--- Advocate Node 실행 ---")

    # --- 필요한 LLM 클라이언트 가져오기 ---
    try:
        # Advocate는 주로 깊이 있는 분석보다는 긍정적 관점 제시에 집중하므로
        # 필요에 따라 high_perf 또는 fast 모델을 선택할 수 있습니다. 여기서는 high_perf 사용.
        llm_advocate = get_high_performance_llm()
        # 구조화된 출력 사용 설정
        structured_llm = llm_advocate.with_structured_output(AdvocateOutput)
    except Exception as e:
        print(f"Advocate: LLM 클라이언트 로드 실패 - {e}")
        return {"error_message": f"LLM 클라이언트 로드 실패: {e}"}

    # --- 상태 정보 읽기 ---
    try:
        messages = state['messages']
        # Critic의 마지막 출력을 가져옵니다. (GraphState에 last_critic_output이 Dict 형태라고 가정)
        # 만약 Critic 포인트만 따로 저장한다면 해당 필드를 사용합니다.
        last_critic_output = state.get('last_critic_output')
        critic_points_str = "이전에 제시된 비판 없음."
        if last_critic_output and isinstance(last_critic_output, dict) and last_critic_output.get("comment"):
             critic_points_str = f"참고: 이전에 다음과 같은 비판이 있었습니다:\n{last_critic_output['comment']}"

        # 기타 필요한 상태 정보 (user_input, current_focus 등)
        # 여기서는 간단히 최근 메시지 기록을 활용합니다.
        if not messages:
             return {"error_message": "Advocate 입력 메시지가 비어있습니다."}

    except KeyError as e:
        print(f"Advocate: 상태 객체에서 필수 키 누락 - {e}")
        return {"error_message": f"Advocate 상태 객체 키 누락: {e}"}

    # --- 시스템 프롬프트 구성 (제공된 예시 기반) ---
    system_prompt_text = f"""
# 역할: 당신은 사용자의 아이디어나 주장에 대해 **건설적인 옹호**를 제공하는 AI 옹호자(Advocate)입니다. 당신의 목표는 아이디어의 강점, 잠재력, 혁신성 등 긍정적인 측면을 **논리적 근거**와 함께 강조하고, 사용자가 자신의 생각을 더욱 확신하고 발전시키도록 **현실적으로 격려**하는 것입니다. 당신은 Critic 에이전트의 비판과 균형을 이루며 사용자의 사고를 지원합니다.

# 핵심 지침:
1. **근거 기반 옹호:** 아이디어의 실질적인 강점과 잠재력을 구체적으로 식별하고, 왜 그것이 강점인지 논리적인 이유나 (필요시 현실적인) 긍정적 증거를 들어 설명하세요. 막연한 칭찬은 피하세요.
2. **긍정적 측면 집중:** 아이디어의 독창성, 시장 잠재력, 사용자 가치, 실현 가능성 등 긍정적인 측면을 부각하세요.
3. **균형 잡힌 시각:** 제공된 Critic의 비판점(`{critic_points_str}`)을 인지하고, 이를 완전히 무시하기보다는 해당 약점을 인정하면서도 강점으로 상쇄하거나 해결 가능한 문제로 **건설적으로 재구성**하세요. Critic처럼 약점을 깊이 파고들지 않는 것이 중요합니다.
4. **현실적 격려:** 과장되지 않고 실현 가능한 격려를 통해 사용자의 동기를 부여하세요.
5. **핵심 집중 응답 (매우 중요):** **매 턴마다 가장 중요하고 설득력 있는 단 하나의 핵심 옹호 포인트 또는 긍정적 재구성에만 집중하여 응답하세요.** 여러 장점을 나열하지 마세요.
6. **구조화된 출력:** 응답의 명확성과 '단일 포인트' 제약 준수를 위해 반드시 지정된 JSON 형식({{"advocacy_point": "...", "brief_elaboration": "..."}})으로 출력해야 합니다.
7. **어조:** 긍정적이고 지지적이며 격려하는 어조를 유지하세요. 사용자의 아이디어에 대한 열정을 보여주되, 현실성을 잃지 마세요.

# Few-Shot 예제 가이드:
* (여기에 긍정적/격려적 어조로, JSON 형식에 맞춰 단일 옹호 포인트를 제시하는 구체적인 예시들을 삽입합니다. Critic 의견을 참조하여 균형을 맞추는 예시 포함)
* 예시1:
    * 입력 컨텍스트: 사용자 아이디어 "반려동물용 자동 번역기", Critic 비판 "기술적 실현 가능성 낮음"
    * 당신의 출력 (JSON): {{"advocacy_point": "획기적인 아이디어입니다! 반려동물과의 소통 문제는 많은 보호자들의 오랜 염원이었습니다.", "brief_elaboration": "기술적 장벽은 존재하지만, AI 음성 인식 및 동물 행동 분석 기술의 발전 속도를 고려할 때 장기적으로 충분히 도전해볼 만한 가치가 있는 혁신적인 목표입니다."}}
* 예시2:
    * 입력 컨텍스트: 사용자 아이디어 "폐플라스틱 재활용 소셜 벤처"
    * 당신의 출력 (JSON): {{"advocacy_point": "환경 문제 해결에 직접 기여하면서 사회적 가치를 창출하는 의미있는 사업 모델입니다.", "brief_elaboration": "최근 ESG 경영과 친환경 소비 트렌드가 확산되면서 정부 지원이나 투자 유치 가능성도 높아, 시장 성장 잠재력이 충분하다고 판단됩니다."}}

# 출력 지침: 위 역할과 지침, 예제를 엄격히 따라서, 현재 대화 맥락에 가장 적합한 단일 옹호 포인트와 설명을 담은 JSON 객체를 생성하세요.
"""

    # --- LLM 입력 메시지 생성 ---
    # TODO: 효과적인 컨텍스트 관리를 위해 메시지 필터링/요약 로직 개선 필요
    prompt_messages: List[BaseMessage] = [SystemMessage(content=system_prompt_text.strip())]
    prompt_messages.extend(messages[-5:]) # 예시: 최근 5개 메시지만 포함 (조정 필요)

    # --- LLM 호출 (구조화된 출력 사용) ---
    model_name_to_log = getattr(llm_advocate, 'model', getattr(llm_advocate, 'model_name', 'N/A'))
    print(f"Advocate: LLM 호출 준비 (Model: {model_name_to_log}, Structured Output: AdvocateOutput)")

    try:
        # structured_llm 사용 및 ainvoke 호출
        response_object: AdvocateOutput = await structured_llm.ainvoke(prompt_messages)
        print(f"Advocate: LLM 응답 수신 (구조화됨) - Point: {response_object.advocacy_point[:50]}...")

        # 사용자에게 전달할 최종 응답 문자열 생성 (예시)
        final_response_string = f"**[Advocate의 견해]**\n\n**핵심:** {response_object.advocacy_point}\n\n**부연:** {response_object.brief_elaboration}"

    except Exception as e:
        error_msg = f"Advocate: LLM 호출 오류 - {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        # 오류 발생 시 오류 메시지를 포함한 상태 반환
        return {
            "error_message": error_msg,
            # 메시지 목록에 오류 발생 AIMessage 추가 가능
            "messages": [AIMessage(content=f"(시스템 오류: Advocate 응답 생성 실패 - {e})")]
        }

    # --- 상태 업데이트 준비 ---
    updates_to_state = {
        # Advocate의 응답을 메시지 리스트에 AIMessage로 추가
        "messages": [AIMessage(content=final_response_string)],
        # 필요시 Advocate의 구조화된 출력을 별도 필드에 저장
        # "last_advocate_output": response_object.dict(),
        "error_message": None, # 성공 시 오류 없음
    }
    print(f"Advocate: 상태 업데이트 반환 - { {k: v for k, v in updates_to_state.items() if k != 'messages'} }")

    return updates_to_state