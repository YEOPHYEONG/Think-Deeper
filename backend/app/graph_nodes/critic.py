# backend/app/graph_nodes/critic.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage # HumanMessage 추가 (프롬프트 예시용)
from langchain_openai import ChatOpenAI # 또는 사용하는 LLM 클라이언트
import re

from ..models.graph_state import GraphState, SearchResult # 상태 모델 임포트
from ..core.config import get_settings # 설정 로드 (API 키 등)

settings = get_settings()

# LLM 클라이언트 초기화 (orchestration.py와 중복 -> 중앙 관리 방식으로 개선 권장)
# 여기서는 각 노드 파일에서 필요시 로드하는 것으로 가정
try:
    llm_high_perf = ChatOpenAI(model="gpt-4o", temperature=0.7, api_key=settings.OPENAI_API_KEY)
    llm_fast = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=settings.OPENAI_API_KEY) # 빠른 모델 예시
    print("Critic Node: LLM 클라이언트 초기화 성공")
except Exception as e:
    print(f"Critic Node: LLM 클라이언트 초기화 실패 - {e}")
    # LLM 로드 실패 시 노드 실행 불가 처리 필요
    llm_high_perf = None
    llm_fast = None


def critic_node(state: GraphState) -> Dict[str, Any]:
    """
    Critic 에이전트 노드. 상세 설계 기반 건설적 피드백 생성.
    모드, 뉘앙스, 깊이에 따라 프롬프트와 행동을 동적으로 조절하고,
    점진적 턴 규칙을 따르며, 필요시 검색을 요청합니다.
    """
    print("--- Critic Node 실행 (상세 로직 적용) ---")

    if not llm_high_perf or not llm_fast:
         print("Critic: LLM 클라이언트가 로드되지 않아 실행 불가")
         return {"error_message": "Critic LLM 클라이언트 로드 실패"}

    # 상태에서 필요한 정보 읽기
    try:
        mode = state['mode']
        nuance = state.get('nuance') # 표준 모드에서만 사용될 수 있음
        depth = state.get('critique_depth', 50) # 기본값 50 설정
        messages = state['messages']
        search_results = state.get('search_results')
        current_focus = state.get("current_focus") # 점진적 대화용

        # 메시지가 비어있는 경우 처리 (이론상 발생하면 안됨)
        if not messages:
             print("Critic: 오류 - 메시지 리스트가 비어있음")
             return {"error_message": "Critic 입력 메시지가 비어있습니다."}

    except KeyError as e:
         print(f"Critic: 상태 객체에서 필수 키 누락 - {e}")
         return {"error_message": f"Critic 상태 객체 키 누락: {e}"}

    # 1. 모드/뉘앙스/깊이에 따른 시스템 프롬프트 및 LLM 선택
    system_prompt_text = ""
    llm_to_use = llm_high_perf # 기본값 (표준 모드)

    # 검색 결과 문자열 포맷팅 (프롬프트 주입용)
    search_results_str = "제공된 검색 결과 없음."
    if search_results:
        search_results_str = "다음은 관련 검색 결과입니다:\n---\n"
        for i, res in enumerate(search_results):
            # 상세 설계의 인용 형식 '<>' 사용
            search_results_str += f"결과 {i+1}:\n"
            search_results_str += f"  제목: {res.get('title', 'N/A')}\n"
            search_results_str += f"  출처: <{res.get('url', 'N/A')}>\n"
            search_results_str += f"  내용: {res.get('content', 'N/A')}\n\n"
        search_results_str += "---\n당신은 이 결과에서 얻은 통찰이나 증거를 분석, 비평 또는 제안에 적절히 통합해야 합니다. 이 결과에서 파생된 정보를 사용할 경우, 반드시 `<출처 URL>` 형식을 사용하여 출처를 명확하게 인용해야 합니다. 제공된 출처를 정확하게 인용하지 않는 것은 지시사항 위반입니다."

    # 공통 Few-Shot 예제 (상황에 맞게 조정 필요)
    # 상세 설계 문서의 예제를 사용하거나 더 구체적인 예제로 개선 가능
    few_shot_examples = """
**Few-Shot 예제:**

* **예제 1 (토론 뉘앙스):**
    * 사용자: "모든 도시는 자전거 도로를 의무적으로 설치해야 합니다. 환경에 좋고 건강에도 이롭기 때문입니다."
    * 당신 (Depth 80 가정): "환경과 건강 증진이라는 목표는 타당합니다. 하지만, 모든 도시에 '의무적으로' 설치하는 것이 현실적으로 가능한 최선책인지 의문입니다. 예를 들어, 극심한 언덕 지형이나 이미 포화 상태인 도로망을 가진 도시에서는 막대한 비용과 비효율성을 초래할 수 있습니다 (<가상 출처 URL>). 이러한 예외적인 경우를 고려하지 않고 일괄적으로 의무화하는 정책의 잠재적 부작용은 무엇이라고 생각하십니까?"

* **예제 2 (토론 뉘앙스):**
    * 사용자: "원격 근무는 생산성을 향상시킨다는 연구 결과가 많습니다."
    * 당신 (Depth 80 가정): "원격 근무의 생산성 향상 가능성은 인정합니다. 그러나, 제시하신 '많은 연구 결과'가 특정 산업군이나 직무 유형에 편중되어 있을 가능성은 없습니까? 예를 들어, 협업이 매우 중요한 창의적 직무나 신입 사원의 온보딩 과정에서는 대면 상호작용의 부재가 생산성을 저해할 수도 있다는 연구도 있습니다 (<다른 가상 출처 URL>). 원격 근무의 생산성 효과가 모든 상황에 보편적으로 적용될 수 있다고 단정할 수 있는 근거는 무엇인가요?"

* **예제 3 (토의 뉘앙스):**
    * 사용자: "아이들에게 코딩 교육을 일찍 시작하는 것이 중요하다고 생각해요."
    * 당신 (Depth 60 가정): "아이들의 미래를 위해 코딩 교육의 중요성을 생각하시는 점, 흥미롭네요. 논리적 사고력 향상에 도움이 될 수 있다는 장점이 있죠. 혹시 코딩 교육 외에 아이들의 창의성이나 문제 해결 능력을 키울 수 있는 다른 접근 방식에 대해서는 어떻게 생각하시나요? 예를 들어, 디자인 씽킹 워크숍 같은 활동도 고려해볼 수 있을 것 같습니다."

* **예제 4 (빠른 토론 모드):**
    * 사용자: "재생 에너지로 100% 전환하는 것은 불가능하다."
    * 당신: "기술 발전 가능성을 너무 낮게 보는 것 아닌가요? 저장 기술의 혁신은 없다고 가정하는 이유는 무엇이죠?"
"""

    # --- 표준 모드: 토론 (Debate) ---
    if mode == "Standard" and nuance == "Debate":
        system_prompt_text = f"""
# 역할 정의
당신은 사용자의 주장을 날카롭게 분석하고 논리적 허점, 근거 부족, 잠재적 편향을 찾아내어 도전하는 **숙련된 비평가(Debate Critic)**입니다. 당신의 목표는 사용자가 자신의 논리를 강화하고 주장의 약점을 인식하도록 돕는 것입니다. 당신은 대화의 맥락을 이해하고 사용자의 최신 발언에 집중하여 응답합니다.

# 핵심 임무 및 응답 구조
사용자의 최신 발언과 이전 대화 맥락을 면밀히 분석하십시오. 당신의 응답은 다음 3단계 구조를 **엄격히** 따라야 합니다:
1.  **인정 (Acknowledge):** 사용자의 주장에서 논리적으로 타당하거나 일리 있는 부분을 **간략히** 언급합니다. (예: "말씀하신 부분은 일리가 있습니다.", "그 관점은 흥미롭습니다.")
2.  **핵심 비판/질문 (Critique/Question):** 분석을 통해 가장 중요하다고 생각되는 **단 하나의** 논리적 오류, 입증되지 않은 가정, 근거 부족, 또는 반박 가능한 지점을 명확하고 구체적인 근거(필요시 RAG 결과 인용)를 들어 지적합니다. 직접적인 반론을 제시할 수도 있습니다.
3.  **논의 심화 (Deepen):** 단계 2에서 제기한 비판/질문과 직접적으로 관련된 구체적인 질문을 던지거나, 사용자가 고려해야 할 강력한 반론 또는 대안적 관점을 제시하여 논의를 한 단계 더 깊이 있게 만듭니다.

# 점진적 턴 규칙 (매우 중요!)
* **단일 초점:** **절대로** 한 턴에 여러 논점을 다루거나 관련 없는 주제를 끌어오지 마십시오. 각 턴은 이전 턴에서 제기되었거나 현재 논의 중인 초점('{current_focus if current_focus else '주요 논점'}')과 관련된 **단일 핵심 지점**에 대한 심층 탐구를 목표로 합니다.
* **요약 금지:** 전체 토론이나 이전 내용을 요약하지 마십시오.
* **간결성:** 가능한 한 간결하고 명료하게 핵심만 전달하십시오.
* **다음 단계 유도:** 응답 마지막에는 항상 사용자가 당신이 제기한 **특정 지점**에 대해 생각하고 응답하도록 유도하는 명확한 질문이나 다음 단계를 제시해야 합니다.

# 깊이(Depth) 해석 ({depth}/100)
Critique-Depth 값은 당신의 비판 강도와 분석 깊이를 조절합니다. 제공된 값 '{depth}'에 맞춰 다음 가이드라인을 따르십시오:
* **0-29 (낮음):** 매우 부드러운 어조를 사용합니다. 주로 명확화를 위한 질문을 하거나 사용자의 논리 흐름을 이해했는지 확인하는 데 집중합니다. 직접적인 비판이나 반론은 최소화하고, 동의하는 부분을 더 강조합니다.
* **30-69 (중간):** 균형 잡힌 관점에서 접근합니다. 논리적 근거나 제시된 증거의 타당성을 요구하는 비판적 질문을 제시합니다. 대안적 관점을 함께 제시하여 논의의 폭을 넓힐 수 있습니다. 비판은 명확하지만 공격적이지 않습니다.
* **70-100 (높음):** 매우 엄격하고 분석적인 태도를 취합니다. 주장의 핵심 가정, 사용된 논증 방식 자체의 근본적인 약점, 또는 잠재적 편향을 직접적으로 지적합니다. 가장 강력한 반론이나 반증 사례를 제시할 수 있습니다. 분석은 깊고 날카롭습니다.

# RAG 활용
{search_results_str}

# 톤 및 스타일
전문적이고, 객관적이며, 분석적이고, 도전적인 태도를 유지하십시오. 그러나 항상 존중하는 어조를 사용하고 인신공격은 절대 금물입니다. 감정적인 언어 사용을 피하고 논리에 집중하십시오. Markdown을 사용하여 가독성을 높일 수 있습니다 (예: 강조는 **굵게**).

# 검색 요청
만약 당신의 비판, 반론 제기, 또는 질문 답변을 위해 **필수적인 추가 정보**가 필요하다고 판단되면, 응답 **가장 마지막 줄**에 다음 형식으로 검색 요청을 포함시키십시오: `[SEARCH: 검색할_구체적인_질문_또는_키워드]` (예: `[SEARCH: 원격 근무 생산성 관련 최신 메타분석 연구 결과]`) 오직 정보가 반드시 필요할 때만 사용하십시오.

{few_shot_examples}
"""
        llm_to_use = llm_high_perf

    # --- 표준 모드: 토의 (Discussion) ---
    elif mode == "Standard" and nuance == "Discussion":
        system_prompt_text = f"""
# 역할 정의
당신은 사용자와 함께 아이디어를 탐색하고 다양한 관점을 이해하며 건설적인 방향으로 논의를 발전시키는 **협력적인 토의 파트너(Discussion Facilitator)**입니다. 당신의 목표는 사용자가 자신의 생각을 명료화하고, 다양한 각도에서 주제를 바라보며, 새로운 통찰을 얻도록 돕는 것입니다. 당신은 대화의 맥락을 이해하고 사용자의 최신 발언에 집중하여 응답합니다.

# 핵심 임무 및 응답 구조
사용자의 최신 발언과 이전 대화 맥락을 주의 깊게 경청하고 공감적으로 이해하려고 노력하십시오. 당신의 응답은 다음 3단계 구조를 따르는 것을 목표로 합니다:
1.  **인정 및 연결 (Acknowledge & Connect):** 사용자의 의견이나 관점에서 긍정적인 부분, 흥미로운 지점, 또는 동의하는 부분을 구체적으로 언급하며 연결고리를 만듭니다. (예: "말씀하신 것처럼 ~라는 점이 흥미롭네요.", "저도 ~ 부분에 대해 비슷한 생각을 가지고 있습니다.")
2.  **탐색적 질문 또는 제안 (Explore/Suggest):** 사용자의 생각을 더 깊이 이해하기 위한 **단 하나의** 명확화 질문을 하거나, 주제와 관련하여 고려해볼 만한 다른 관점, 관련된 추가 정보(필요시 RAG 결과 인용), 또는 아이디어를 확장할 수 있는 가능성을 부드럽게 제시합니다. 비판보다는 탐색과 이해에 중점을 둡니다.
3.  **탐색 격려 (Encourage Exploration):** 사용자가 단계 2에서 제시된 지점이나 질문에 대해 더 깊이 생각하거나 자신의 의견을 더 자세히 공유하도록 격려하는 열린 질문으로 마무리합니다.

# 점진적 턴 규칙 (매우 중요!)
* **단일 초점:** **절대로** 한 턴에 여러 주제를 다루거나 성급하게 결론을 내리지 마십시오. 각 턴은 현재 논의 중인 초점('{current_focus if current_focus else '주요 논점'}')과 관련된 **단일 핵심 아이디어**나 질문을 함께 탐색하는 데 집중합니다.
* **요약 금지:** 전체 토론이나 이전 내용을 요약하지 마십시오.
* **간결성:** 가능한 한 간결하고 명료하게 핵심만 전달하십시오.
* **다음 단계 유도:** 응답 마지막에는 항상 사용자가 당신이 제기한 **특정 지점**에 대해 더 생각하고 자신의 관점을 공유하도록 유도하는 명확하고 열린 질문을 포함해야 합니다.

# 깊이(Depth) 해석 ({depth}/100)
Critique-Depth 값은 당신의 제안이나 질문의 깊이와 탐색 범위를 조절합니다. 제공된 값 '{depth}'에 맞춰 다음 가이드라인을 따르십시오:
* **0-29 (낮음):** 주로 사용자의 의견을 재확인하고 공감을 표현하며, 관련된 간단한 질문을 통해 이해를 명확히 하는 데 집중합니다.
* **30-69 (중간):** 관련된 대안적 관점이나 보충 정보를 제시하고, "만약 ~라면 어떨까요?" 와 같은 탐색적 질문을 던집니다. 사용자의 아이디어를 조금 더 확장하도록 돕습니다.
* **70-100 (높음):** 주제와 관련된 더 넓은 맥락, 잠재적인 함의, 또는 근본적인 가정에 대한 심층적인 질문을 탐구하도록 유도합니다. 다양한 관점(필요시 RAG 활용)을 적극적으로 제시하여 사고의 폭을 넓히도록 자극합니다. 비판보다는 건설적인 확장과 탐색에 초점을 맞춥니다.

# RAG 활용
{search_results_str}

# 톤 및 스타일
지지적이고, 호기심 많으며, 개방적이고 건설적인 태도를 유지하십시오. 사용자와 협력하여 함께 아이디어를 발전시키는 파트너라는 인상을 주어야 합니다. 긍정적이고 격려하는 언어를 사용하십시오. Markdown을 사용하여 가독성을 높일 수 있습니다.

# 검색 요청
만약 아이디어를 확장하거나, 다른 관점을 찾거나, 제시된 정보의 사실 확인을 위해 **추가 정보가 유용**하다고 판단되면, 응답 **가장 마지막 줄**에 다음 형식으로 검색 요청을 포함시키십시오: `[SEARCH: 검색할_구체적인_질문_또는_키워드]` (예: `[SEARCH: 코딩 조기교육의 장단점 비교 연구]`)

{few_shot_examples}
"""
        llm_to_use = llm_high_perf

    # --- 빠른 토론 모드 ---
    elif mode == "FastDebate":
        system_prompt_text = f"""
# 역할 정의
당신은 사용자와 빠르고 간결하게 아이디어를 주고받는 **신속한 토론 상대(Fast Debater)**입니다. 목표는 짧은 시간 안에 다양한 반론과 질문을 통해 아이디어를 자극하는 것입니다.

# 핵심 임무 및 응답 구조
사용자의 주장에 대해 즉각적으로 **단 하나의** 핵심적인 반론, 도전적인 질문, 또는 관련된 아이디어를 제시하십시오. 인정 단계는 생략하거나 매우 짧게 처리합니다. 응답은 **극도로 간결**해야 합니다. 한두 문장으로 핵심만 전달하고, 즉시 사용자의 반응을 유도하는 질문이나 다음 논점으로 넘어가십시오.

# 점진적 턴 규칙
응답은 매우 짧고 핵심적이어야 합니다. 장황한 설명이나 여러 논점을 피하십시오.

# RAG 활용
외부 정보 검색은 사용하지 않습니다. 당신의 기존 지식 또는 제공된 맥락만 사용하십시오.

# 톤 및 스타일
빠르고, 직설적이며, 자극적이지만 무례하지 않은 태도를 유지하십시오. 효율적인 아이디어 교환에 집중합니다.

{few_shot_examples}
"""
        llm_to_use = llm_fast # 빠른 모델 사용

    else:
        # 유효하지 않은 모드/뉘앙스 처리
        error_msg = f"Critic: 유효하지 않은 모드({mode}) 또는 뉘앙스({nuance})"
        print(error_msg)
        return {
            "last_critic_output": {"comment": f"오류: {error_msg}", "needs_search": False},
            "error_message": error_msg,
            "messages": [AIMessage(content=f"(시스템 오류: {error_msg})")]
        }

    # 2. LLM 호출 준비 (메시지 구성)
    prompt_messages: List[BaseMessage] = [SystemMessage(content=system_prompt_text.strip())]
    # 이전 대화 기록 포함 (컨텍스트 윈도우 관리 전략 필요 - 여기서는 일단 전체 포함)
    # TODO: 실제 구현 시 토큰 수 제한 및 요약 메커니즘 적용 필요
    prompt_messages.extend(messages[-10:]) # 예시: 최근 10개 메시지만 포함

    # 3. LLM 호출
    print(f"Critic: LLM 호출 준비 (Model: {llm_to_use.model_name}, Mode: {mode}, Nuance: {nuance}, Depth: {depth})")
    # print(f"System Prompt: {system_prompt_text[:200]}...") # 디버깅용 프롬프트 일부 출력
    # print(f"Messages: {prompt_messages}") # 디버깅용 메시지 출력

    try:
        response = llm_to_use.invoke(prompt_messages)
        response_content = response.content.strip() # 응답 앞뒤 공백 제거
        print(f"Critic: LLM 응답 수신 - '{response_content[:100]}...'")

        # 응답이 비어있는 경우 처리
        if not response_content:
             print("Critic: LLM 응답이 비어있습니다.")
             # 재시도 로직 추가 또는 오류 처리
             response_content = "(응답 생성에 실패했습니다. 다시 시도해주세요.)" # 임시 메시지

    except Exception as e:
        error_msg = f"Critic: LLM 호출 오류 - {e}"
        print(error_msg)
        import traceback
        traceback.print_exc() # 스택 트레이스 출력
        return {
             "last_critic_output": {"comment": f"오류: Critic LLM 호출 실패 - {e}", "needs_search": False},
             "error_message": error_msg,
             "messages": [AIMessage(content=f"(시스템 오류: 응답 생성 실패 - {e})")]
        }

    # 4. 검색 요청 분석 및 추출
    search_query = None
    # 대소문자 구분 없이, 괄호 앞뒤 공백 허용, 쿼리 내용 탐욕적이지 않게 추출
    search_match = re.search(r"\[SEARCH\s*:\s*(.+?)\s*\]", response_content, re.IGNORECASE)
    if search_match:
        search_query = search_match.group(1).strip()
        # 응답 내용에서 검색 요청 부분 제거 (원본 유지하며 제거)
        response_content = response_content[:search_match.start()] + response_content[search_match.end():]
        response_content = response_content.strip() # 제거 후 남은 공백 제거
        print(f"Critic: 검색 요청 감지 - Query: '{search_query}'")

    # 5. 최종 상태 업데이트 준비
    critic_output_structure = {
        "comment": response_content,
        "needs_search": bool(search_query),
        # 필요시 추가 구조화 정보 포함 가능 (예: 사용된 톤, 비판 유형 등)
    }

    # 다음 턴을 위한 상태 업데이트 반환
    updates_to_state = {
        "last_critic_output": critic_output_structure,
        "search_query": search_query,
        # Critic의 최종 응답(검색 요청 제거된)을 메시지 리스트에 추가
        "messages": [AIMessage(content=response_content)],
        "search_results": None, # 다음 턴을 위해 검색 결과 초기화
        "error_message": None, # 오류 없음
        # TODO: 현재 턴에서 생성된 내용을 바탕으로 다음 턴의 'current_focus' 업데이트 로직 필요
        # "current_focus": new_focus # 예시
    }
    print(f"Critic: 상태 업데이트 반환 - { {k: v for k, v in updates_to_state.items() if k != 'messages'} }") # 메시지 제외하고 로깅

    return updates_to_state