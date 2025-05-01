# backend/app/graph_nodes/critic.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from pydantic import BaseModel, Field
from ..core.llm_provider import get_high_performance_llm, get_fast_llm
import re
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.tools import tool

from ..models.graph_state import GraphState, SearchResult

# --- 구조화된 출력을 위한 Pydantic 모델 정의 ---
class CriticOutput(BaseModel):
    critique_point: str = Field(description="가장 중요하다고 판단되는 단 하나의 핵심 비판 내용입니다. 명확하고 간결하게 작성하세요.")
    brief_elaboration: str = Field(description="해당 비판점에 대한 1-2 문장의 간결한 부연 설명 또는 사용자가 생각해볼 질문입니다.")
    request_search_query: Optional[str] = Field(None, description="null 또는 Search 에이전트에게 요청할 구체적인 검색 쿼리 문자열")


async def critic_node(state: GraphState) -> Dict[str, Any]:
    """ Critic 에이전트 노드 (LLM Provider 및 구조화된 출력 사용) """
    print("--- Critic Node 실행 ---")
    try:
        llm_critic = get_high_performance_llm() # Critic용 LLM
        structured_llm = llm_critic.with_structured_output(CriticOutput)
    except Exception as e:
        print(f"Critic: LLM 클라이언트 로드 실패 - {e}")
        return {"error_message": f"LLM 클라이언트 로드 실패: {e}"}

    try:
        # 상태 읽기 (mode, nuance는 1:1 모드에서는 사용 안 할 수 있음)
        depth = state.get('critique_depth', 50)
        messages = state['messages']
        search_results = state.get('search_results')
        current_focus = state.get("current_focus")
        if not messages: return {"error_message": "Critic 입력 메시지가 비어있습니다."}
    except KeyError as e:
        return {"error_message": f"Critic 상태 객체 키 누락: {e}"}

    # 검색 결과 문자열 포맷팅 (이전과 동일)
    search_results_str = "제공된 검색 결과 없음."
    if search_results: # ... (이전 코드와 동일하게 search_results_str 생성) ...
        search_results_str = "다음은 관련 검색 결과입니다:\n---\n"
        for i, res in enumerate(search_results):
            search_results_str += f"결과 {i+1}: 제목: {res.get('title', 'N/A')}, 출처: <{res.get('url', 'N/A')}>\n 내용: {res.get('content', 'N/A')}\n\n"
        search_results_str += "---\n 당신은 이 결과에서 얻은 통찰이나 증거를 분석, 비평 또는 제안에 적절히 통합하고, 반드시 `<출처 URL>` 형식으로 인용해야 합니다."


    # --- 시스템 프롬프트 (1:1 모드 고려하여 단순화 가능) ---
    # 보고서의 Critic 프롬프트를 기반으로 작성, 구조화된 출력 지침 포함
    system_prompt_text = f"""
# 역할: 당신은 사용자의 아이디어나 주장에 대해 **건설적인 비판**을 제공하는 AI 비평가(Critic)입니다. 목표는 논리적 약점, 근거 부족, 잠재적 위험, 숨겨진 가정 등을 **구체적으로 식별**하여 사용자가 아이디어를 **개선하고 강화**하도록 돕는 것입니다.

# 핵심 지침:
1. **건설적 분석:** 구체적인 약점이나 문제점을 지적하세요.
2. **논리/가정 검토:** 논리 비약, 불충분한 근거, 암묵적 가정을 명확히 지적하고 질문하세요.
3. **위험/한계 식별:** 현실적인 위험, 단점, 어려움을 제시하세요.
4. **RAG 활용 및 검색 요청:**
   - 제공된 검색 결과가 있다면({{search_results_str}}) 먼저 이를 분석하여 당신의 비판이나 부연 설명에 통합하고, 반드시 `<출처 URL>` 형식으로 인용해야 합니다.
   - 만약, (1) 제공된 검색 결과가 없거나, (2) 제공된 결과만으로는 당신의 핵심 비판을 뒷받침하기에 정보가 명백히 불충분하거나, (3) 현재 비판과 관련하여 완전히 새로운 정보가 반드시 필요하다고 판단될 경우에만, 출력 JSON의 `request_search_query` 필드에 검색할 구체적인 질문이나 키워드를 포함시키세요.
   - 그 외의 모든 경우에는 `request_search_query` 필드를 null 또는 빈 문자열로 두어야 합니다. 불필요한 검색 요청은 하지 마세요.
5. **핵심 집중:** **매 턴 가장 중요한 단 하나의 비판점/질문에만 집중하세요.**
6. **구조화된 출력:** 반드시 지정된 JSON 형식(`{{ "critique_point": "...", "brief_elaboration": "...", "request_search_query": "..." | null }}`)으로 출력하세요.
7. **어조:** 분석적, 객관적, 성장을 돕는 톤.

# 입력 컨텍스트 활용:
* 사용자의 마지막 메시지(`{{messages[-1].content}}` - *참고: 이 f-string 변수 삽입은 실제로는 작동하지 않으므로, 프롬프트 생성 전에 값을 문자열에 넣어야 합니다*)를 주로 분석하세요.
* 현재 논의 초점(`{{current_focus}}` - *이것도 마찬가지*)을 고려하세요.

# Few-Shot 예제 가이드:
* (단일 비판점과 설명을 JSON 형식으로 제공하는 예시 추가 - request_search_query 사용 예시 포함)
* 예시 1 (검색 불필요): {{"critique_point": "제시된 통계 자료의 출처가 불분명하여 신뢰성을 판단하기 어렵습니다.", "brief_elaboration": "해당 통계가 어떤 기관에서 어떤 방식으로 조사되었는지 구체적인 출처 정보가 필요합니다. 출처에 따라 데이터의 해석이 달라질 수 있습니다.", "request_search_query": null}}
* 예시 2 (검색 필요): {{"critique_point": "주장하신 '최근 연구 결과'에 대한 구체적인 내용 확인이 필요합니다.", "brief_elaboration": "언급하신 연구 결과를 직접 검토하여 주장의 타당성을 평가해야 합니다. 어떤 연구를 말씀하시는지요?", "request_search_query": "원격 근무 생산성 관련 최신 메타분석 연구 결과"}}

# 출력 지침: 위 역할과 지침, 예제를 엄격히 따라서, 현재 대화 맥락에 가장 적합한 단일 비판 포인트, 설명, 그리고 필요한 경우 검색 쿼리를 담은 JSON 객체를 생성하세요.
"""

    # LLM 입력 메시지 생성 (이전과 유사, 컨텍스트 길이 조절 필요)
    prompt_messages: List[BaseMessage] = [SystemMessage(content=system_prompt_text.strip())]
    prompt_messages.extend(messages[-5:]) # 최근 5개 메시지 (조절 필요)

    # LLM 호출 (구조화된 출력 사용)
    model_name_to_log = getattr(llm_critic, 'model', getattr(llm_critic, 'model_name', 'N/A'))
    print(f"Critic: LLM 호출 준비 (Model: {model_name_to_log}, Structured Output: CriticOutput)")
    try:
        response_object: CriticOutput = await structured_llm.ainvoke(prompt_messages)
        print(f"Critic: LLM 응답 수신 (구조화됨) - Point: {response_object.critique_point[:50]}...")

        # 최종 응답 문자열 생성 (예시)
        final_response_string = f"**[Critic의 검토]**\n\n**핵심:** {response_object.critique_point}\n\n**의견:** {response_object.brief_elaboration}"
        search_query = response_object.request_search_query # 검색 쿼리 추출

    except Exception as e: # 오류 처리
        error_msg = f"Critic: LLM 호출 오류 - {e}"
        return {"error_message": error_msg, "messages": [AIMessage(content=f"(시스템 오류: Critic 응답 생성 실패)")]}

    # 상태 업데이트 준비
    updates_to_state = {
        "messages": [AIMessage(content=final_response_string)],
        "last_critic_output": response_object.dict(), # 구조화된 결과 저장
        "search_query": search_query, # 검색 쿼리 상태 업데이트
        "search_results": None,
        "error_message": None,
    }
    print(f"Critic: 상태 업데이트 반환 - Search Query: {search_query}")
    return updates_to_state