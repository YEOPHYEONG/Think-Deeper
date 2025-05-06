# backend/app/graph_nodes/why/free_conversation_node.py

from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from ...core.llm_provider import get_high_performance_llm
# WhyGraphState는 타입 힌팅용으로 유지
from ...models.why_graph_state import WhyGraphState

class HistorySummaryOutput(BaseModel):
    summary: str = Field(..., description="16턴 이전 대화를 한 문단으로 요약한 내용입니다.")

# state 타입을 Dict[str, Any] 또는 WhyGraphState (TypedDict)로 받을 수 있음
async def free_conversation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Free Conversation 노드:
    최종 요약 및 대화 이력을 바탕으로 사용자와 자유롭게 대화합니다.
    """
    print("[FREE][DEBUG] Entering free_conversation_node")

    # ===== 수정된 부분: state 접근 방식을 .get()으로 변경 =====
    messages: List[BaseMessage] = state.get('messages', [])
    channel_values = state.get('channel_values', {})

    # messages 리스트가 비어있으면 channel_values에서 복원 시도
    if not messages and channel_values:
        all_msgs = []
        for ch_msgs in channel_values.values():
            all_msgs.extend([msg for msg in ch_msgs if isinstance(msg, BaseMessage)])
        messages = all_msgs
        print(f"[FREE][DEBUG] Restored messages from channel_values: {len(messages)} messages")

    # 상태 읽기
    findings_summary = state.get('findings_summary', 'N/A')
    full_history: List[Dict[str,str]] = state.get('dialogue_history', [])
    older_summary = state.get('older_history_summary', '') # 기본값 빈 문자열
    # ========================================================

    # history 분리
    RECENT_N = 15
    if len(full_history) > RECENT_N:
        recent_history = full_history[-RECENT_N:]
        older_history  = full_history[:-RECENT_N]
    else:
        recent_history = full_history
        older_history  = []

    # older_history_summary 생성 (최초 1회 또는 주기적 갱신 로직 필요 시 추가)
    state_updates: Dict[str,Any] = {}
    if older_history and not older_summary:
        print("[FREE][INFO] Generating summary for older history...")
        try:
            llm_summarizer = get_high_performance_llm().with_structured_output(HistorySummaryOutput)
            system_p = "다음 대화의 핵심 내용을 간결히 한 문단으로 요약하세요."
            human_p  = "\n".join(f"{turn.get('role')}: {turn.get('content', '')}" for turn in older_history)
            hist_out = await llm_summarizer.ainvoke([ SystemMessage(content=system_p),
                                           HumanMessage(content=human_p) ])
            older_summary = hist_out.summary
            state_updates['older_history_summary'] = older_summary
            print(f"[FREE][DEBUG] Generated older history summary: {older_summary}")
        except Exception as e:
            print(f"[FREE][ERROR] Failed to generate older history summary: {e}")
            older_summary = "(과거 대화 요약 생성 실패)" # 오류 발생 시 기본값
            state_updates['older_history_summary'] = older_summary


    # system_prompt 구성
    sys_parts = [
        "당신은 사용자와 자유롭게 대화하는 AI입니다. 아래 제공된 이전 'Why 탐색' 요약과 최근 대화 내용을 참고하여 대화를 이어나가세요.",
        f"1) 'Why 탐색' 요약:\n{findings_summary}",
        f"2) 최근 대화 (최대 {RECENT_N}턴):\n" +
          "\n".join(f"- {h.get('role')}: {h.get('content', '')}" for h in recent_history)
    ]
    if older_summary:
        sys_parts.append(f"3) 과거 대화 요약:\n{older_summary}")

    system_prompt = "\n\n".join(sys_parts)

    # LLM 호출 및 interrupt
    # 가장 최근 메시지가 사용자 메시지인지 확인
    if not messages or not isinstance(messages[-1], HumanMessage):
         # 사용자 입력이 없는 경우, 먼저 사용자 입력을 요청하는 메시지 반환 고려
         # 여기서는 일단 오류 메시지 반환 또는 기본 응답 생성
         print("[FREE][WARN] Last message is not from user. Cannot generate response without user input.")
         ai_text = "이전 대화 내용을 바탕으로 어떤 이야기를 더 나누고 싶으신가요?"
         # 또는 raise interrupt("Please provide your input.")
    else:
        user_last_msg = messages[-1]
        print(f"[FREE][DEBUG] Last user message: {user_last_msg.content}")
        print(f"[FREE][DEBUG] System prompt for free conversation: {system_prompt}")
        llm = get_high_performance_llm()
        try:
            print("[FREE][INFO] Calling LLM for free conversation...")
            # 일반 텍스트 출력이므로 structured_output 불필요
            response = await llm.ainvoke([ SystemMessage(content=system_prompt),
                                           HumanMessage(content=user_last_msg.content) ])
            ai_text = response.content if hasattr(response, 'content') else str(response)
            print("[FREE][INFO] LLM call completed.")
            print(f"[FREE][DEBUG] Generated response: {ai_text}")
        except Exception as e:
            print(f"[FREE][ERROR] LLM 호출 실패: {e}")
            import traceback
            traceback.print_exc()
            ai_text = f"(시스템 오류: 응답 생성 실패 - {e})"


    # 상태 업데이트 후 인터럽트 (사용자에게 응답 전달)
    interrupt_data = {
        **state_updates, # older_summary 갱신 포함 가능
        "messages": messages + [AIMessage(content=ai_text)],
        "assistant_message": ai_text # 오케스트레이터용 메시지
    }
    print(f"[FREE][DEBUG] Raising interrupt with response: {ai_text}")
    # 자유 대화는 계속 interrupt를 통해 사용자 입력을 받음
    raise interrupt(ai_text).with_data(interrupt_data)

