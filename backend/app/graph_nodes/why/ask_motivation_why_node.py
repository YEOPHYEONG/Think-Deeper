# backend/app/graph_nodes/why/ask_motivation_why_node.py

from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field

# LLM Provider 및 상태 모델 임포트
from ...core.llm_provider import get_high_performance_llm
# from ...models.why_graph_state import WhyGraphState # 실제 정의된 WhyGraphState 임포트 가정
from ...models.why_graph_state import WhyGraphState

# 구조화된 출력을 위한 Pydantic 모델 정의
class MotivationQuestionOutput(BaseModel):
    """첫 동기 질문 생성 모델"""
    motivation_question: str = Field(description="파악된 아이디어를 바탕으로 사용자의 근본적인 동기나 목적을 묻는 가장 적절한 단 하나의 개방형 질문입니다.")
    # rationale: Optional[str] = Field(None, description="해당 질문을 선택한 간단한 이유 (내부 로깅/디버깅용)")

async def ask_motivation_why_node(state: WhyGraphState) -> Dict[str, Any]:
    """
    Ask Motivation Why 노드: 파악된 아이디어 요약을 바탕으로
    사용자의 핵심 동기(Why)를 묻는 첫 번째 질문을 생성하고 메시지에 추가합니다.
    (수정됨: 입력 상태 확인 로직 우선 실행)
    """
    print("--- Ask Motivation Why Node 실행 ---")

    # --- 1. 상태 정보 읽기 및 필수 입력 확인 (LLM 로드 전) ---
    try:
        # 이전 노드에서 생성한 아이디어 요약을 가져옴
        idea_summary = state.get('idea_summary')
        # *** 중요: idea_summary 확인을 먼저 수행 ***
        if not idea_summary:
            print("AskMotivationWhy Error: idea_summary is missing in state.")
            # idea_summary가 없으면 LLM 호출 없이 즉시 오류 반환
            return {"error_message": "AskMotivationWhy: 상태에 아이디어 요약(idea_summary)이 없습니다."}

        messages = state.get('messages', []) # 메시지 기록 참조 (선택적)

    except KeyError as e:
        print(f"AskMotivationWhy: 상태 객체에서 필수 키 누락 - {e}")
        return {"error_message": f"AskMotivationWhy 상태 객체 키 누락: {e}"}
    # --- ---

    # --- 2. LLM 클라이언트 가져오기 (입력 확인 후) ---
    try:
        llm_questioner = get_high_performance_llm() # 통찰력 있는 질문 생성을 위해 고성능 모델 사용
        structured_llm = llm_questioner.with_structured_output(MotivationQuestionOutput)
    except Exception as e:
        # LLM 로드 실패는 실행 환경 문제일 수 있음 (예: API 키)
        print(f"AskMotivationWhy: LLM 클라이언트 로드 실패 - {e}")
        # LLM 로드 실패 시 사용자에게 보여줄 메시지 생성 및 반환
        error_content = f"(시스템 오류: 질문 생성 준비 중 오류 발생 - {e})"
        # 기존 메시지에 오류 메시지 누적
        return {
            "error_message": f"LLM 클라이언트 로드 실패: {e}",
            "messages": messages + [AIMessage(content=error_content)]
        }

    # --- ---

    # --- 3. 시스템 프롬프트 구성 ---
    # 이제 idea_summary가 존재함이 보장됨
    system_prompt_text = f"""
# 역할: 당신은 사용자의 아이디어나 생각 이면에 있는 **근본적인 동기, 목적, 또는 추구하는 가치('Why')**를 탐색하도록 돕는 AI 질문자입니다. 당신의 목표는 사용자가 제시한 아이디어 요약을 바탕으로, 그 아이디어를 추진하게 만드는 **가장 핵심적인 이유**에 대해 성찰하도록 유도하는 **단 하나의 통찰력 있는 개방형 질문**을 던지는 것입니다. (참고: 골든 서클 - Why -> How -> What)
#단, 근본적인 동기, 목적은 개인이 성취하고자하는 목적보다 그 아이디어가 구체화되어 해결할 문제, 혹은 가치에 집중해야합니다.
# 입력 정보:
* **사용자 아이디어 요약:** {idea_summary}

# 핵심 지침:
1.  **동기 집중:** 제공된 아이디어 요약을 기반으로, 사용자가 이 아이디어를 통해 **궁극적으로 무엇을 성취하고 싶은지, 어떤 변화를 만들고 싶은지, 또는 이것이 왜 중요하다고 생각하는지** 등 근본적인 'Why'에 초점을 맞춘 질문을 하세요.
2.  **개방형 질문:** 사용자가 자신의 생각을 자세히 설명하도록 유도하는 질문을 하세요. (예: "왜...", "어떤...", "무엇을...")
3.  **호기심과 존중:** 진심으로 궁금하다는 듯, 사용자의 아이디어를 존중하는 어조를 유지하세요.
4.  **단일 질문:** **가장 중요하다고 생각되는 단 하나의 동기 질문**만 생성하세요.
5.  **구조화된 출력:** 반드시 지정된 JSON 형식(`{{"motivation_question": "..."}}`)으로 질문을 출력하세요.
6.  

# 출력 지침: 위 역할과 지침에 따라, 제공된 아이디어 요약에 대해 사용자의 핵심 동기를 탐색하는 가장 적절한 단일 질문을 JSON 객체로 생성하세요.
"""
    # --- ---

    # 4. LLM 호출
    prompt_messages: List[BaseMessage] = [
        SystemMessage(content=system_prompt_text.strip())
    ]

    try:
        response_object: MotivationQuestionOutput = await structured_llm.ainvoke(prompt_messages)
        ai_question_content = response_object.motivation_question
        error_message_to_return = None
        print(f"AskMotivationWhy: 질문 생성 완료 → {ai_question_content[:60]}...")

    except Exception as e:
        import traceback
        traceback.print_exc()
        ai_question_content = f"(시스템 오류: 동기 질문 생성 실패 - {e})"
        error_message_to_return = str(e)

    # 5. 인터럽트 발생 (사용자 입력 대기)
    print("AskMotivationWhy: 질문 생성 후 interrupt 발생 → 사용자 응답 대기 중단")
    raise interrupt(ai_question_content).with_data({
        "messages": messages + [AIMessage(content=ai_question_content)],
        "error_message": error_message_to_return,
    })

