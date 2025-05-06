# backend/app/graph_nodes/why/findings_summarization_node.py

from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from ...core.llm_provider import get_high_performance_llm
# WhyGraphState는 타입 힌팅용으로 유지
from ...models.why_graph_state import WhyGraphState

class FindingsSummaryOutput(BaseModel):
    findings_summary: str = Field(
        ...,
        description=(
            "지금까지 대화된 내용을 바탕으로 원래 아이디어, 동기, 탐색된 각 가정 및 주요 인사이트를 한눈에 보기 좋게 정리한 요약입니다."
        )
    )

# state 타입을 Dict[str, Any] 또는 WhyGraphState (TypedDict)로 받을 수 있음
async def findings_summarization_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Findings Summarization 노드:
    지금까지 진행된 대화 내용을 바탕으로 아이디어, 동기 및 탐색된 각 가정과 주요 인사이트를
    정리한 요약을 생성하고 사용자에게 전달합니다.
    """
    print("[FIND][DEBUG] Entering findings_summarization_node")

    # ===== 수정된 부분: state 접근 방식을 .get()으로 변경 =====
    messages: List[BaseMessage] = state.get('messages', [])
    channel_values = state.get('channel_values', {})

    # messages 리스트가 비어있으면 channel_values에서 복원 시도
    if not messages and channel_values:
        all_msgs = []
        for ch_msgs in channel_values.values():
            all_msgs.extend([msg for msg in ch_msgs if isinstance(msg, BaseMessage)])
        messages = all_msgs
        print(f"[FIND][DEBUG] Restored messages from channel_values: {len(messages)} messages")

    # 상태 읽기
    raw_topic: str = state.get('raw_topic', 'N/A')
    raw_idea: str = state.get('raw_idea', 'N/A')
    # motivation_summary 또는 final_motivation_summary 사용
    motivation_summary: str = state.get('motivation_summary') or state.get('final_motivation_summary', 'N/A')
    identified_assumptions: List[str] = state.get('identified_assumptions', [])
    dialogue_history: List[Dict[str, str]] = state.get('dialogue_history', [])
    # ========================================================

    # LLM 준비
    llm = get_high_performance_llm()
    structured_llm = llm.with_structured_output(FindingsSummaryOutput)

    # 시스템 및 유저 프롬프트 구성
    system_prompt = (
        "지금까지 대화된 내용을 바탕으로,\n"
        "1) 원래 아이디어\n"
        "2) 그 동기(목적)\n"
        "3) 탐색된 각 가정 및 주요 인사이트\n"
        "를 한눈에 보기 좋게 정리하세요."
    )
    user_prompt = (
        f"Topic: {raw_topic}\n"
        f"Idea: {raw_idea}\n"
        f"Motivation Summary: {motivation_summary}\n"
        "Identified Assumptions and Probing (Based on Dialogue History):\n"
        # 가정과 탐색 내용을 dialogue_history에서 추출하거나,
        # probed_assumptions와 관련된 답변을 별도 저장했다면 사용
        # 여기서는 일단 가정 목록만 표시 (LLM이 대화 이력에서 파악하도록 유도)
    )
    if identified_assumptions:
        for assumption in identified_assumptions:
            user_prompt += f"- {assumption}\n"
    else:
        user_prompt += "(No assumptions identified or probed yet)\n"

    user_prompt += "Dialogue History (최근 15턴):\n"
    if dialogue_history:
        for turn in dialogue_history[-15:]:
            role = 'User' if turn.get('role') == 'user' else 'Assistant'
            user_prompt += f"- {role}: {turn.get('content', '')}\n"
    else:
        user_prompt += "(No dialogue history available)\n"

    print(f"[FIND][DEBUG] user_prompt for findings summary: {user_prompt}")

    # LLM 호출
    try:
        print("[FIND][INFO] Calling LLM for findings summarization...")
        output: FindingsSummaryOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        summary: str = output.findings_summary
        print("[FIND][INFO] LLM call completed.")
        print(f"[FIND][DEBUG] Findings summary: {summary}")
    except Exception as e:
        print(f"[FIND][ERROR] LLM 호출 실패: {e}")
        import traceback
        traceback.print_exc()
        summary = f"(시스템 오류: 결과 정리 실패 - {e})"

    # 상태 업데이트 및 메시지 생성
    ai_msg = summary
    # 인터럽트 발생 시 반환할 상태 업데이트
    interrupt_data = {
        'messages': messages + [AIMessage(content=ai_msg)],
        'findings_summary': summary,
        'assumptions_fully_probed': True, # 이 노드는 모든 가정 탐색 후 실행됨
        'assistant_message': ai_msg # 오케스트레이터용 메시지
    }
    print(f"[FIND][DEBUG] Raising interrupt with findings summary: {ai_msg}")

    # 인터럽트로 결과 전달 (사용자에게 최종 요약 보여줌)
    raise interrupt(ai_msg).with_data(interrupt_data)
