# backend/app/graph_nodes/why/free_conversation_node.py

from typing import Dict, Any, List, Union
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.types import interrupt # interrupt 임포트
from pydantic import BaseModel, Field # Pydantic 모델 사용

from ...core.llm_provider import get_high_performance_llm
from ...models.why_graph_state import WhyGraphState # 타입 힌팅용

class HistorySummaryOutput(BaseModel):
    summary: str = Field(..., description="16턴 이전 대화를 한 문단으로 요약한 내용입니다.")

async def free_conversation_node(state: Dict[str, Any]) -> Dict[str, Any]: # Interrupt를 발생시키므로 반환 타입은 사실상 None
    """
    Free Conversation 노드:
    최종 요약 및 대화 이력을 바탕으로 사용자와 자유롭게 대화하고,
    AI의 응답을 interrupt를 통해 전달합니다 (assistant_message를 상태에 포함).
    """
    print("[FREE][DEBUG] Entering free_conversation_node")

    messages: List[Union[BaseMessage, dict]] = state.get('messages', [])
    findings_summary_str = state.get('findings_summary', 'N/A (이전 탐색 요약 없음)')
    older_history_summary_str = state.get('older_history_summary', '') 

    # 메시지 이력 문자열화 및 BaseMessage 객체 리스트 준비
    recent_history_lines = []
    current_messages_for_state = [] # BaseMessage 객체로 일관성 유지
    
    # 전체 메시지 이력에서 BaseMessage 객체 추출 및 최근 15턴 분리
    all_base_messages: List[BaseMessage] = []
    for i, msg_data in enumerate(messages):
        msg_obj = None
        if isinstance(msg_data, HumanMessage): msg_obj = msg_data
        elif isinstance(msg_data, AIMessage): msg_obj = msg_data
        elif isinstance(msg_data, dict):
            msg_type = msg_data.get("type")
            raw_content = msg_data.get("content")
            add_kwargs = msg_data.get("additional_kwargs", {})
            if raw_content is not None:
                if msg_type == "human": msg_obj = HumanMessage(content=raw_content, additional_kwargs=add_kwargs)
                elif msg_type == "ai" or msg_type == "assistant": msg_obj = AIMessage(content=raw_content, additional_kwargs=add_kwargs)
        
        if msg_obj: 
            all_base_messages.append(msg_obj)
        elif isinstance(msg_data, dict) and msg_obj is None and msg_data.get("content") is not None : 
             # BaseMessage로 변환 실패했으나 dict 형태이고 내용이 있는 경우 (주의해서 사용)
            all_base_messages.append(AIMessage(content=f"[DictData] {msg_data.get('type')}: {msg_data.get('content')}")) # 임시 처리


    current_messages_for_state = all_base_messages # 다음 상태에 저장될 메시지 리스트

    RECENT_N = 15
    recent_base_messages = all_base_messages[-RECENT_N:]
    older_base_messages = all_base_messages[:-RECENT_N]

    for msg in recent_base_messages:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        recent_history_lines.append(f"- {role}: {msg.content}")

    # older_history_summary 생성 (필요시)
    state_updates_for_interrupt: Dict[str,Any] = {}
    if older_base_messages and not older_history_summary_str: # 과거 대화가 있고, 요약이 아직 없을 때만 생성
        print("[FREE][INFO] Generating summary for older history...")
        try:
            llm_summarizer = get_high_performance_llm().with_structured_output(HistorySummaryOutput)
            older_history_prompt = "\n".join(
                f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}" for m in older_base_messages
            )
            hist_out = await llm_summarizer.ainvoke([
                SystemMessage(content="다음 대화의 핵심 내용을 간결히 한 문단으로 요약하세요."),
                HumanMessage(content=older_history_prompt)
            ])
            older_history_summary_str = hist_out.summary
            state_updates_for_interrupt['older_history_summary'] = older_history_summary_str
            print(f"[FREE][DEBUG] Generated older history summary: {older_history_summary_str}")
        except Exception as e_summ:
            print(f"[FREE][ERROR] Failed to generate older history summary: {e_summ}")
            older_history_summary_str = "(과거 대화 요약 생성 실패)"
            state_updates_for_interrupt['older_history_summary'] = older_history_summary_str
    
    # 시스템 프롬프트 구성
    sys_prompt_parts = [
        "당신은 사용자와 자유롭게 대화하는 AI입니다. 아래 제공된 이전 'Why 탐색' 요약과 최근 대화 내용을 참고하여 대화를 이어나가세요.",
        f"1) 'Why 탐색' 요약:\n{findings_summary_str}",
        f"2) 최근 대화 (최대 {RECENT_N}턴):\n" + "\n".join(recent_history_lines)
    ]
    if older_history_summary_str:
        sys_prompt_parts.append(f"3) 과거 대화 요약 (최근 {RECENT_N}턴 이전):\n{older_history_summary_str}")
    system_prompt_for_llm = "\n\n".join(sys_prompt_parts)

    # LLM 호출 및 interrupt
    ai_response_text: str
    if not current_messages_for_state or not isinstance(current_messages_for_state[-1], HumanMessage):
         print("[FREE][WARN] Last message is not from user, or no messages. Cannot generate response without user input.")
         ai_response_text = "이전 대화 내용을 바탕으로 어떤 이야기를 더 나누고 싶으신가요? 아니면 다른 질문이 있으신가요?"
    else:
        user_last_message_content = current_messages_for_state[-1].content
        print(f"[FREE][DEBUG] Last user message: {user_last_message_content}")
        # print(f"[FREE][DEBUG] System prompt for free conversation: {system_prompt_for_llm}") # 로그가 너무 길어질 수 있음
        llm = get_high_performance_llm()
        try:
            print("[FREE][INFO] Calling LLM for free conversation...")
            llm_response_obj = await llm.ainvoke([
                SystemMessage(content=system_prompt_for_llm),
                HumanMessage(content=user_last_message_content) # 사용자의 마지막 발화 전달
            ])
            ai_response_text = llm_response_obj.content if hasattr(llm_response_obj, 'content') else str(llm_response_obj)
            print("[FREE][INFO] LLM call completed.")
            print(f"[FREE][DEBUG] Generated response: {ai_response_text}")
        except Exception as e_llm_call:
            print(f"[FREE][ERROR] LLM 호출 실패: {e_llm_call}")
            # import traceback; traceback.print_exc()
            ai_response_text = f"(시스템 오류: 자유 대화 응답 생성 실패 - {e_llm_call})"

    # 상태 업데이트 후 인터럽트 (사용자에게 응답 전달)
    updated_messages_with_free_chat = current_messages_for_state + [AIMessage(content=ai_response_text)]
    
    interrupt_data_for_free_chat = {
        **state_updates_for_interrupt, # older_history_summary 갱신 포함 가능
        "messages": updated_messages_with_free_chat,
        "assistant_message": ai_response_text  # <<< *** 중요: 사용자에게 보여줄 AI 응답을 명시적 키로 추가 ***
    }
    print(f"[FREE][DEBUG] Raising interrupt with response: {ai_response_text[:100]}...")
    raise interrupt(ai_response_text).with_data(interrupt_data_for_free_chat)
