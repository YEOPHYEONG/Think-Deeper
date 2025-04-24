# backend/app/graph_nodes/moderator.py
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage
from langchain_openai import ChatOpenAI # 또는 사용하는 LLM 클라이언트

from ..models.graph_state import GraphState
from ..core.config import get_settings # 설정 로드 (API 키 등)

settings = get_settings()

# LLM 클라이언트 초기화 (빠른 모델 사용 권장)
try:
    # orchestration.py 와 중복 정의 -> 개선 필요
    llm_fast = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=settings.OPENAI_API_KEY)
    print("Moderator Node: LLM 클라이언트 초기화 성공")
except Exception as e:
    print(f"Moderator Node: LLM 클라이언트 초기화 실패 - {e}")
    llm_fast = None

def moderator_node(state: GraphState) -> Dict[str, Any]:
    """
    Moderator 노드: /summarize 처리, 토론 품질 관리 (기본), 최종 응답 설정
    """
    print("--- Moderator Node 실행 ---")

    flags = state.get('moderator_flags', [])
    last_critic_output = state.get('last_critic_output')
    messages = state['messages']
    final_response_content: str | None = None
    error_msg: str | None = None

    try:
        # 1. /summarize 명령어 처리
        if "summarize_request" in flags:
            print("Moderator: /summarize 요청 처리 중")
            if not llm_fast:
                 raise RuntimeError("요약 기능을 위한 LLM 클라이언트가 로드되지 않았습니다.")
            if not messages:
                 raise ValueError("요약을 위한 메시지가 없습니다.")

            # 상세 설계 III.B.2 기반 프롬프트
            summary_prompt_text = """
당신은 "Think Deeper" 토론/토의의 **중재자(Moderator)**입니다. 당신의 임무는 사용자의 요청에 따라 현재까지의 대화 기록을 바탕으로 주요 논점, 핵심 주장, 합의점, 이견 등을 객관적으로 요약하여 제공하는 것입니다. 요약은 간결하고 명확해야 합니다.

다음 대화 기록을 요약해주십시오:
"""
            # 요약 대상 메시지 선정 (예: 전체 또는 최근 N개)
            # 여기서는 일단 전체 메시지 사용
            summary_messages: List[BaseMessage] = [SystemMessage(content=summary_prompt_text)]
            summary_messages.extend(messages) # 전체 메시지 포함

            print(f"Moderator: 요약 생성 LLM 호출 (메시지 {len(summary_messages)}개)")
            summary_response = llm_fast.invoke(summary_messages)
            final_response_content = f"**대화 요약:**\n\n{summary_response.content.strip()}"
            print("Moderator: 요약 생성 완료")

        # 2. (구현 필요) 토론 품질 관리 로직 (상세 설계 II.E, IV.A)
        # 예: 논점 이탈 감지, 반복 패턴 식별, 건설성 평가 등
        # if is_off_topic(messages):
        #     final_response_content = "(알림) 대화가 원래 주제에서 벗어난 것 같습니다. 다시 집중해볼까요?"
        # elif is_repetitive(messages):
        #     final_response_content = "(알림) 같은 논점이 반복되고 있습니다. 다른 관점에서 접근해보는 것은 어떨까요?"

        # 3. 최종 응답 결정
        if final_response_content:
            # 요약 또는 품질 관리 메시지가 생성된 경우
            print(f"Moderator: 최종 응답 결정됨 (요약/관리 메시지) - '{final_response_content[:50]}...'")
            pass # final_response_content 사용
        elif last_critic_output and isinstance(last_critic_output, dict):
            # Critic 노드의 출력을 최종 응답으로 사용
            final_response_content = last_critic_output.get("comment")
            if not final_response_content:
                 print("Moderator: Critic 출력에서 comment 찾을 수 없음")
                 final_response_content = "(오류: 응답 내용을 찾을 수 없습니다.)"
            print(f"Moderator: 최종 응답 결정됨 (Critic 출력) - '{final_response_content[:50]}...'")
        else:
            # Critic 출력도 없는 경우 (오류 상황)
            error_msg = "Moderator: 최종 응답으로 사용할 내용을 찾을 수 없습니다."
            print(error_msg)
            final_response_content = f"(시스템 오류: {error_msg})"


        # 4. 상태 업데이트 준비
        updates = {
            "final_response": final_response_content,
            "moderator_flags": [],  # 처리 후 플래그 초기화
            "error_message": error_msg # 오류 메시지 설정
        }
        # Moderator의 응답(요약 등)도 메시지 기록에 추가할지 여부 결정 필요
        # updates["messages"] = [AIMessage(content=final_response_content)]

        return updates

    except Exception as e:
        error_msg = f"Moderator 노드 오류 발생: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {"error_message": error_msg, "final_response": f"(시스템 오류: {error_msg})"}