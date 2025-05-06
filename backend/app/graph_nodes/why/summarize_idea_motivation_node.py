# backend/app/graph_nodes/why/summarize_idea_motivation_node.py

from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field

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
    3) 사용자에게 요약 결과를 전달
    """
    print("[SUMMZ][DEBUG] Entering summarize_idea_motivation_node")

    # ===== 수정된 부분: state 접근 방식을 .get()으로 변경 =====
    messages: List[BaseMessage] = state.get('messages', [])
    channel_values = state.get('channel_values', {})

    # messages 리스트가 비어있으면 channel_values에서 복원 시도
    if not messages and channel_values:
        all_msgs = []
        for ch_msgs in channel_values.values():
            all_msgs.extend([msg for msg in ch_msgs if isinstance(msg, BaseMessage)])
        messages = all_msgs
        print(f"[SUMMZ][DEBUG] Restored messages from channel_values: {len(messages)} messages")

    # 상태 읽기
    raw_topic: str = state.get('raw_topic', 'N/A') # 기본값 추가
    raw_idea: str = state.get('raw_idea', 'N/A')   # 기본값 추가
    final_motivation: str = state.get('final_motivation_summary', 'N/A') # 기본값 추가
    dialogue_history: List[Dict[str, str]] = state.get('dialogue_history', [])
    # ========================================================

    # LLM 준비
    llm = get_high_performance_llm()
    structured_llm = llm.with_structured_output(SummarizeIdeaMotivationOutput)

    # 시스템 및 유저 프롬프트 구성
    system_prompt = (
        "다음 내용을 참고하여, 원래 아이디어와 그 동기(목적)를 명확히 요약하세요."
    )
    user_prompt = (
        f"Topic: {raw_topic}\n"
        f"Idea: {raw_idea}\n"
        f"Motivation: {final_motivation}\n"
        f"Dialogue History:"
    )
    # dialogue_history가 비어있을 경우 대비
    if dialogue_history:
        for turn in dialogue_history:
            role = 'User' if turn.get('role') == 'user' else 'Assistant'
            user_prompt += f"\n- {role}: {turn.get('content', '')}"
    else:
        user_prompt += "\n(No dialogue history available)"

    print(f"[SUMMZ][DEBUG] user_prompt for summarization: {user_prompt}")

    # LLM 호출
    try:
        print("[SUMMZ][INFO] Calling LLM for summarization...")
        output: SummarizeIdeaMotivationOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        ai_idea = output.idea_summary
        ai_motivation = output.motivation_summary
        print("[SUMMZ][INFO] LLM call completed.")
        print(f"[SUMMZ][DEBUG] Summarized Idea: {ai_idea}")
        print(f"[SUMMZ][DEBUG] Summarized Motivation: {ai_motivation}")
    except Exception as e:
        print(f"[SUMMZ][ERROR] LLM 호출 실패: {e}")
        import traceback
        traceback.print_exc()
        ai_idea = f"(시스템 오류: 아이디어 요약 실패 - {e})"
        ai_motivation = f"(시스템 오류: 동기 요약 실패 - {e})"

    # 메시지 조합 및 상태 업데이트
    ai_msg = (
        f"**아이디어 요약**:\n{ai_idea}\n\n"
        f"**동기 요약**:\n{ai_motivation}"
    )
    # 다음 노드로 전달할 상태 업데이트
    return_state = {
        'messages': messages + [AIMessage(content=ai_msg)],
        'idea_summary': ai_idea,
        'motivation_summary': ai_motivation,
        'assistant_message': ai_msg # 오케스트레이터용 메시지
    }
    print(f"[SUMMZ][DEBUG] Returning state: {return_state}")

    # 이 노드는 interrupt 없이 다음 노드로 진행하므로 상태 딕셔너리 반환
    return return_state
