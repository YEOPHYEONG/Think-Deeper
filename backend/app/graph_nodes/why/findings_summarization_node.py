# backend/app/graph_nodes/why/findings_summarization_node.py

from typing import Dict, Any, List, Union
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.types import interrupt # interrupt 임포트
from pydantic import BaseModel, Field # Pydantic 모델 사용

from ...core.llm_provider import get_high_performance_llm
from ...models.why_graph_state import WhyGraphState # 타입 힌팅용

class FindingsSummaryOutput(BaseModel):
    findings_summary: str = Field(
        ...,
        description=(
            "지금까지 대화된 내용을 바탕으로 원래 아이디어, 동기, 탐색된 각 가정 및 주요 인사이트를 한눈에 보기 좋게 정리한 요약입니다."
        )
    )

async def findings_summarization_node(state: Dict[str, Any]) -> Dict[str, Any]: # Interrupt를 발생시키므로 반환 타입은 사실상 None
    """
    Findings Summarization 노드:
    지금까지 진행된 대화 내용을 바탕으로 아이디어, 동기 및 탐색된 각 가정과 주요 인사이트를
    정리한 요약을 생성하고 사용자에게 전달하기 위해 interrupt를 발생시킵니다 (assistant_message를 상태에 포함).
    """
    print("[FIND][DEBUG] Entering findings_summarization_node")

    messages: List[Union[BaseMessage, dict]] = state.get('messages', [])
    raw_topic: str = state.get('raw_topic', 'N/A')
    raw_idea: str = state.get('raw_idea', 'N/A')
    final_motivation: str = state.get('final_motivation_summary') or state.get('motivation_summary', 'N/A')
    identified_assumptions: List[str] = state.get('identified_assumptions', [])
    # probed_assumptions와 그에 대한 답변은 messages 리스트에서 LLM이 추론하도록 유도
    
    # 메시지 이력 문자열화 (LLM 프롬프트용)
    history_lines_for_prompt = []
    current_messages_for_state = [] # BaseMessage 객체로 일관성 유지
    for i, msg_data in enumerate(messages):
        role = None; content = None; msg_obj = None
        if isinstance(msg_data, HumanMessage): 
            role, content, msg_obj = "User", msg_data.content, msg_data
        elif isinstance(msg_data, AIMessage): 
            role, content, msg_obj = "Assistant", msg_data.content, msg_data
        elif isinstance(msg_data, dict):
            msg_type = msg_data.get("type")
            raw_content = msg_data.get("content")
            if msg_type == "human": 
                role, content = "User", raw_content
                if raw_content is not None: msg_obj = HumanMessage(content=raw_content, additional_kwargs=msg_data.get("additional_kwargs",{}))
            elif msg_type == "ai" or msg_type == "assistant": 
                role, content = "Assistant", raw_content
                if raw_content is not None: msg_obj = AIMessage(content=raw_content, additional_kwargs=msg_data.get("additional_kwargs",{}))
        
        if role and content is not None:
            history_lines_for_prompt.append(f"- {role}: {content}")
        if msg_obj: 
            current_messages_for_state.append(msg_obj)
        elif isinstance(msg_data, dict) and msg_obj is None and content is not None : 
            current_messages_for_state.append(msg_data)

    # LLM 준비
    llm = get_high_performance_llm()
    structured_llm = llm.with_structured_output(FindingsSummaryOutput)

    # 시스템 및 유저 프롬프트 구성
    system_prompt_str = (
        "지금까지 대화된 내용을 바탕으로,\n"
        "1) 원래 아이디어\n"
        "2) 그 동기(목적)\n"
        "3. 탐색된 각 가정 및 주요 인사이트 (대화 내용에서 추론하여 가정별로 정리)\n"
        "를 한눈에 보기 좋게 정리하세요. 각 가정에 대한 탐색 결과와 사용자의 답변에서 드러난 핵심 내용을 포함해야 합니다."
    )
    user_prompt_str = (
        f"Topic: {raw_topic}\n"
        f"Original Idea: {raw_idea}\n"
        f"Final Motivation Summary: {final_motivation}\n"
        "Identified Assumptions (to be detailed based on dialogue):\n"
    )
    if identified_assumptions:
        for assumption in identified_assumptions:
            user_prompt_str += f"- {assumption}\n"
    else:
        user_prompt_str += "(No specific assumptions were listed for probing, summarize based on overall dialogue)\n"
    
    user_prompt_str += "\nFull Dialogue History (for context and assumption insights):\n"
    # 전체 대화 이력을 전달하여 LLM이 가정별 인사이트를 더 잘 추출하도록 함
    user_prompt_str += "\n".join(history_lines_for_prompt)

    print(f"[FIND][DEBUG] user_prompt for findings summary (length {len(user_prompt_str)}): {user_prompt_str[:500]}...")

    # LLM 호출
    generated_summary: str
    try:
        print("[FIND][INFO] Calling LLM for findings summarization...")
        llm_output: FindingsSummaryOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt_str),
            HumanMessage(content=user_prompt_str)
        ])
        generated_summary = llm_output.findings_summary
        print("[FIND][INFO] LLM call completed.")
        print(f"[FIND][DEBUG] Findings summary: {generated_summary}")
    except Exception as e:
        print(f"[FIND][ERROR] LLM 호출 실패: {e}")
        # import traceback; traceback.print_exc()
        generated_summary = f"(시스템 오류: 결과 정리 실패 - {e})"

    # 상태 업데이트 및 메시지 생성
    updated_messages_with_summary = current_messages_for_state + [AIMessage(content=generated_summary)]
    
    interrupt_data_for_findings = {
        'messages': updated_messages_with_summary,
        'findings_summary': generated_summary, # 생성된 요약을 상태에 저장
        'assumptions_fully_probed': True, # 이 노드는 모든 가정 탐색 후 실행됨을 가정
        'assistant_message': generated_summary  # <<< *** 중요: 사용자에게 보여줄 최종 메시지를 명시적 키로 추가 ***
    }
    print(f"[FIND][DEBUG] Raising interrupt with findings summary: {generated_summary[:100]}...")
    raise interrupt(generated_summary).with_data(interrupt_data_for_findings)
