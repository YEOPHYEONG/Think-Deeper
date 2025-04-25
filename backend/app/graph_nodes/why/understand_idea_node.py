# backend/app/graph_nodes/why/understand_idea_node.py

from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from langchain_core.pydantic_v1 import BaseModel, Field

# LLM Provider 및 상태 모델 임포트 (Why 흐름 상태 모델은 추후 정의 필요)
# 여기서는 일단 기존 GraphState를 사용한다고 가정하고, 필요시 WhyGraphState로 변경
from ...core.llm_provider import get_fast_llm # 아이디어 요약은 빠른 모델 사용 가능
from ...models.graph_state import GraphState # 또는 WhyGraphState

# 구조화된 출력을 위한 Pydantic 모델 정의
class IdeaSummaryOutput(BaseModel):
    """사용자 아이디어 요약 모델"""
    idea_summary: str = Field(description="사용자가 제시한 아이디어의 핵심 내용(What/How)을 간결하게 요약한 문장입니다.")
    identified_what: Optional[str] = Field(None, description="파악된 '무엇을' 하려는지에 대한 요약")
    identified_how: Optional[str] = Field(None, description="파악된 '어떻게' 하려는지에 대한 요약 (제시된 경우)")

async def understand_idea_node(state: GraphState) -> Dict[str, Any]:
    """
    Understand Idea 노드: 사용자의 초기 아이디어 제시 메시지를 분석하여
    핵심 아이디어(What/How)를 요약하고 상태에 저장합니다.
    """
    print("--- Understand Idea Node 실행 ---")

    # LLM 클라이언트 가져오기
    try:
        llm_summarizer = get_fast_llm() # 요약 작업이므로 빠른 모델 사용
        structured_llm = llm_summarizer.with_structured_output(IdeaSummaryOutput)
    except Exception as e:
        print(f"UnderstandIdea: LLM 클라이언트 로드 실패 - {e}")
        return {"error_message": f"LLM 클라이언트 로드 실패: {e}"}

    # 상태 정보 읽기
    try:
        messages = state['messages']
        if not messages:
             return {"error_message": "UnderstandIdea: 입력 메시지가 비어있습니다."}

        # 일반적으로 이 노드는 첫 턴에 실행되므로, 마지막 메시지가 사용자 아이디어일 가능성이 높음
        last_user_message = messages[-1]
        if not isinstance(last_user_message, HumanMessage):
            # 만약 마지막 메시지가 사용자 메시지가 아니라면 오류 처리 또는 다른 로직 필요
            # 예를 들어, 사용자가 '/explore why' 같은 명령어로 시작했을 경우 등
            print("UnderstandIdea: 마지막 메시지가 사용자 입력이 아닙니다. 아이디어 파악 건너뛰기 또는 오류 처리 필요.")
            # 이 경우, 다음 노드로 바로 넘어가거나, 사용자에게 아이디어를 명확히 해달라고 요청하는 로직 추가 가능
            # 여기서는 일단 간단히 오류 메시지 반환
            return {"error_message": "Why 흐름 시작을 위한 사용자 아이디어가 명확하지 않습니다."}

        user_idea_text = last_user_message.content

    except KeyError as e:
        print(f"UnderstandIdea: 상태 객체에서 필수 키 누락 - {e}")
        return {"error_message": f"UnderstandIdea 상태 객체 키 누락: {e}"}

    # 시스템 프롬프트 구성
    system_prompt_text = """
# 역할: 당신은 사용자가 제시한 아이디어나 생각을 분석하여 핵심 내용을 간결하게 요약하는 AI 분석가입니다. 사용자의 발언에서 '무엇을(What)' 하려고 하는지, 그리고 가능하다면 '어떻게(How)' 하려고 하는지를 명확히 파악하는 것이 목표입니다.

# 핵심 지침:
1. **핵심 아이디어 식별:** 사용자의 발언 전체를 읽고, 제안하는 주요 아이디어, 프로젝트, 또는 의견이 무엇인지 파악하세요.
2. **What/How 분리 (가능하다면):** 아이디어의 핵심 목표나 대상(What)과 그것을 달성하려는 구체적인 방법이나 접근 방식(How)을 구분해 보세요. 항상 명확히 구분되지 않을 수도 있습니다.
3. **간결한 요약:** 파악된 내용을 바탕으로, 아이디어의 핵심을 1-2 문장으로 명확하게 요약하세요.
4. **구조화된 출력:** 반드시 지정된 JSON 형식(`{"idea_summary": "...", "identified_what": "...", "identified_how": "..."}`)으로 출력하세요. 'identified_what'과 'identified_how'는 파악된 경우에만 채우고, 아니면 null로 두세요.

# 출력 지침: 위 역할과 지침에 따라 사용자 발언의 핵심 아이디어를 요약한 JSON 객체를 생성하세요.
"""

    # LLM 입력 메시지 생성 (사용자의 마지막 발언만 사용)
    prompt_messages: List[BaseMessage] = [
        SystemMessage(content=system_prompt_text.strip()),
        HumanMessage(content=user_idea_text) # 요약 대상인 사용자 메시지
    ]

    # LLM 호출
    model_name_to_log = getattr(llm_summarizer, 'model', getattr(llm_summarizer, 'model_name', 'N/A'))
    print(f"UnderstandIdea: LLM 호출 준비 (Model: {model_name_to_log}, Structured Output: IdeaSummaryOutput)")

    try:
        response_object: IdeaSummaryOutput = await structured_llm.ainvoke(prompt_messages)
        print(f"UnderstandIdea: LLM 응답 수신 (구조화됨) - Summary: {response_object.idea_summary[:50]}...")

    except Exception as e:
        error_msg = f"UnderstandIdea: LLM 호출 오류 - {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            "error_message": error_msg,
            # 메시지에 오류를 직접 추가하지는 않음 (Coordinator 등에서 처리)
        }

    # 상태 업데이트 준비
    # (주의: 실제 GraphState 또는 WhyGraphState 모델에 맞게 필드명 조정 필요)
    updates_to_state = {
        "idea_summary": response_object.idea_summary, # 요약된 아이디어를 상태에 저장
        "identified_what": response_object.identified_what,
        "identified_how": response_object.identified_how,
        "error_message": None, # 성공 시 오류 없음
        # 이 노드는 사용자에게 직접 응답하지 않으므로 messages 필드는 건드리지 않음
    }
    print(f"UnderstandIdea: 상태 업데이트 반환 - {updates_to_state}")

    return updates_to_state