# backend/app/graph_nodes/why/summarize_idea_motivation_node.py

from typing import Dict, Any, List, Union
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
# from langgraph.types import interrupt # Interrupt 사용 안 함
from pydantic import BaseModel, Field
import traceback # 에러 로깅용

from ...core.llm_provider import get_high_performance_llm
# WhyGraphState는 타입 힌팅용으로 유지
from ...models.why_graph_state import WhyGraphState

class SummarizeIdeaMotivationOutput(BaseModel):
    idea_summary: str = Field(..., description="요약된 아이디어 내용")
    motivation_summary: str = Field(..., description="요약된 동기/목적 내용")

# state 타입을 Dict[str, Any] 또는 WhyGraphState (TypedDict)로 받을 수 있음
async def summarize_idea_motivation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summarize Idea & Motivation 노드:
    1) 최종 동기 요약(final_motivation_summary)과 원본 아이디어(raw_topic, raw_idea)를 기반으로
    2) 아이디어와 동기 모두 명확히 압축한 요약 생성
    3) 상태 업데이트 후 다음 노드로 진행 (interrupt 없음)
    """
    print("[SUMMZ][NODE_LIFECYCLE] >>> Entering summarize_idea_motivation_node <<<") # 노드 시작 로그

    # 상태 읽기 (오류 발생 가능성 최소화 위해 .get 사용)
    messages: List[Union[BaseMessage, dict]] = state.get('messages', [])
    raw_topic: str = state.get('raw_topic', 'N/A')
    raw_idea: str = state.get('raw_idea', 'N/A')
    final_motivation: str = state.get('final_motivation_summary', 'N/A') # 동기 명확화 단계 결과 사용
    # dialogue_history는 messages로 대체되었으므로 제거 또는 주석 처리
    # dialogue_history: List[Dict[str, str]] = state.get('dialogue_history', [])

    print(f"  [SUMMZ][STATE_IN] raw_topic: '{raw_topic}'")
    print(f"  [SUMMZ][STATE_IN] raw_idea: '{raw_idea}'")
    print(f"  [SUMMZ][STATE_IN] final_motivation_summary: '{final_motivation}'")
    print(f"  [SUMMZ][STATE_IN] messages length: {len(messages)}")

    # 필수 입력 값 확인
    if final_motivation == 'N/A' or raw_idea == 'N/A':
         error_msg = f"Summarize node missing required inputs: final_motivation='{final_motivation}', raw_idea='{raw_idea}'"
         print(f"  [SUMMZ][ERROR] {error_msg}")
         # 오류 상태 반환 (다음 조건부 엣지에서 END로 갈 수 있도록)
         return {
             "messages": messages + [AIMessage(content=f"(시스템 오류: {error_msg})")],
             "error_message": error_msg
         }

    # LLM 준비
    llm = get_high_performance_llm()
    structured_llm = llm.with_structured_output(SummarizeIdeaMotivationOutput)

    # 시스템 및 유저 프롬프트 구성
    system_prompt = (
        "다음 내용을 참고하여, 원래 아이디어와 그 동기(목적)를 명확히 요약하세요."
    )
    # 대화 이력을 프롬프트에 포함할지 여부 결정 (여기서는 제외하고 주요 정보만 사용)
    user_prompt = (
        f"Topic: {raw_topic}\n"
        f"Original Idea: {raw_idea}\n"
        f"Final Motivation: {final_motivation}\n"
        # f"Dialogue History:" # 필요시 주석 해제 및 history_lines 생성 로직 추가
    )

    print(f"  [SUMMZ][DEBUG] user_prompt for summarization:\n{user_prompt}")

    # LLM 호출
    ai_idea = "(아이디어 요약 실패)"
    ai_motivation = "(동기 요약 실패)" # 기본값 설정
    try:
        print("  [SUMMZ][INFO] Calling LLM for summarization...")
        output: SummarizeIdeaMotivationOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        ai_idea = output.idea_summary
        ai_motivation = output.motivation_summary # LLM이 생성한 동기 요약
        print("  [SUMMZ][INFO] LLM call completed.")
        print(f"  [SUMMZ][DEBUG] Summarized Idea: {ai_idea}")
        print(f"  [SUMMZ][DEBUG] Summarized Motivation (from LLM): {ai_motivation}")
    except Exception as e:
        print(f"  [SUMMZ][ERROR] LLM call failed: {e}")
        traceback.print_exc()
        # 오류 발생 시에도 진행은 하되, 오류 메시지를 포함
        error_msg = f"(시스템 오류: 아이디어/동기 요약 실패 - {e})"
        # 상태 업데이트 시 error_message 필드 사용 고려
        # ai_idea, ai_motivation은 기본 실패 메시지 유지

    # 다음 노드로 전달할 상태 업데이트
    # 주의: motivation_summary 키를 사용해야 다음 조건부 엣지가 인식함
    return_state = {
        'messages': messages + [AIMessage(content=f"아이디어 및 동기 요약 완료 (내부 처리)")], # 사용자에게 직접 보이지 않는 내부 처리 메시지
        'idea_summary': ai_idea,
        'motivation_summary': ai_motivation, # 조건부 엣지에서 사용할 키
        'final_motivation_summary': ai_motivation, # final_motivation_summary도 동일한 값으로 설정
        'error_message': error_msg if 'error_msg' in locals() else None # LLM 오류 기록
    }
    print(f"[SUMMZ][NODE_LIFECYCLE] <<< Exiting summarize_idea_motivation_node >>>")
    print(f"  [SUMMZ][STATE_OUT] idea_summary: '{return_state.get('idea_summary')}'")
    print(f"  [SUMMZ][STATE_OUT] motivation_summary: '{return_state.get('motivation_summary')}'")
    print(f"  [SUMMZ][STATE_OUT] error_message: {return_state.get('error_message')}")

    return return_state
