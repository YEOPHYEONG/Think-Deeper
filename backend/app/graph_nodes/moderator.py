# backend/app/graph_nodes/moderator.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from ..core.llm_provider import get_fast_llm # LLM Provider 사용

from ..models.graph_state import GraphState

async def check_discussion_quality(messages: List[BaseMessage]) -> Optional[str]: # 인자 타입 명시 권장
    """
    대화 기록을 바탕으로 품질 문제를 감지하고 메타 코멘트를 반환합니다.
    (상세 구현 필요 - LLM 호출 또는 규칙 기반 분석)
    """
    # --- 실제 코드로 인식될 수 있는 ... 제거 ---

    # TODO: 상세 로직 구현 (LLM 기반 품질 검사 포함)
    # llm_quality_check = get_fast_llm() # 필요시 LLM 로드
    # ... 품질 검사 로직 ...

    # 현재는 임시로 None 반환
    pass # <--- 함수 본문이 비어있음을 나타내는 pass만 남김

    # 또는 바로 None 반환 (함수 시그니처에 맞게)
    # return None
async def moderator_node(state: GraphState) -> Dict[str, Any]:
    """ Moderator 노드 (LLM Provider 사용) """
    print("--- Moderator Node 실행 ---")
    messages = state.get('messages', [])
    flags = state.get('moderator_flags', [])
    # --- 마지막 발언자 확인 (중요) ---
    # 상태에 마지막 에이전트 출력을 저장하는 필드가 필요 (예: last_output)
    # 여기서는 messages 리스트의 마지막 AI 메시지를 사용하거나,
    # last_critic_output, last_advocate_output 등을 확인
    last_agent_output_content: Optional[str] = None
    if messages and isinstance(messages[-1], AIMessage):
         last_agent_output_content = messages[-1].content
    # TODO: 또는 last_critic_output 등에서 가져오는 로직 개선

    final_response_content: str | None = None
    error_msg: Optional[str] = None
    quality_comment: Optional[str] = None

    try:
        # --- LLM 로드 (요약 시에만) ---
        llm_for_summary = None
        if "summarize_request" in flags:
            try: llm_for_summary = get_fast_llm()
            except Exception as e: error_msg = f"요약 LLM 로드 실패: {e}"

        # 1. /summarize 처리
        if "summarize_request" in flags:
            print("Moderator: /summarize 요청 처리 중")
            if error_msg: # LLM 로드 실패 시
                 final_response_content = f"(시스템 오류: {error_msg})"
            elif not messages:
                 final_response_content = "**대화 요약:**\n\n요약할 내용 없음."
            else:
                 # ... (요약 로직 - 이전과 동일, llm_for_summary 사용) ...
                 messages_to_summarize = [m for m in messages if not (isinstance(m, HumanMessage) and m.content.strip().lower() == '/summarize')]
                 if messages_to_summarize and llm_for_summary:
                     summary_prompt = "..." # 요약 프롬프트
                     try:
                          summary_response = await llm_for_summary.ainvoke([SystemMessage(content=summary_prompt)] + messages_to_summarize)
                          final_response_content = f"**대화 요약:**\n\n{summary_response.content.strip()}"
                     except Exception as e:
                          error_msg = f"요약 생성 오류: {e}"
                          final_response_content = f"(시스템 오류: {error_msg})"
                 else:
                     final_response_content = "**대화 요약:**\n\n요약할 내용 없음."

        # 2. 토론 품질 관리 (구현 필요)
        if not final_response_content:
            # quality_comment = await check_discussion_quality(messages)
            pass # 품질 검사 로직 추가

        # 3. 최종 응답 결정
        if final_response_content: pass # 요약 결과 사용
        elif last_agent_output_content: # 마지막 AI 메시지를 최종 응답으로 사용
            if quality_comment: final_response_content = f"{quality_comment}\n\n---\n\n{last_agent_output_content}"
            else: final_response_content = last_agent_output_content
            print(f"Moderator: 최종 응답 결정됨 (Last Agent Output) - '{final_response_content[:50]}...'")
        else: # 응답 생성 실패 또는 오류
            error_msg = error_msg or "Moderator: 최종 응답 내용 없음"
            final_response_content = f"(시스템 오류: {error_msg})"
            print(f"Moderator: 오류 - {error_msg}")

        # 4. 상태 업데이트 준비
        updates = {
            **state,
            "final_response": final_response_content,
            "moderator_flags": [],
            "error_message": error_msg,
        }

        print(f"Moderator: 상태 업데이트 반환 - FinalResponse 설정됨, Error: {error_msg}")
        return updates

    except Exception as e: # 노드 전체 오류
        error_msg = f"Moderator 노드 오류: {e}"
        import traceback; traceback.print_exc()
        final_response_content = f"(시스템 오류: {error_msg})"
        # messages에 오류 메시지를 추가할지 결정 필요
        return { "error_message": error_msg, "final_response": final_response_content }