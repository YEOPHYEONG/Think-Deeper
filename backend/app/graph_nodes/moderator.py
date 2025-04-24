# backend/app/graph_nodes/moderator.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from ..models.graph_state import GraphState
from ..core.config import get_settings

settings = get_settings()

# LLM 클라이언트 초기화
try:
    llm_fast = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, api_key=settings.OPENAI_API_KEY)
    print("Moderator Node: LLM 클라이언트 초기화 성공")
    # 품질 관리를 위한 별도 LLM 또는 동일 LLM 사용 가능
    llm_quality_check = llm_fast # 예시: 동일 모델 사용
except Exception as e:
    print(f"Moderator Node: LLM 클라이언트 초기화 실패 - {e}")
    llm_fast = None
    llm_quality_check = None

# --- (선택적) 토론 품질 검사 함수 (예시) ---
async def check_discussion_quality(messages: List[BaseMessage]) -> Optional[str]:
    """
    대화 기록을 바탕으로 품질 문제를 감지하고 메타 코멘트를 반환합니다.
    (상세 구현 필요 - LLM 호출 또는 규칙 기반 분석)
    """
    if not llm_quality_check:
        return None # LLM 없으면 검사 불가

    # TODO: 상세 로직 구현 (규칙 또는 LLM 기반)
    # 1. 논점 이탈 감지
    # 2. 반복 패턴 감지
    # 3. 비건설적 대화 감지 (예: 과도한 감정 표현, 인신 공격 등)

    # 임시 Placeholder: 간단한 규칙 예시 (길이가 너무 길거나 짧은 응답 등)
    if len(messages) > 20: # 예시: 메시지가 20개 초과 시 환기
         # 실제로는 더 복잡한 분석 필요
         # return "(알림) 대화가 길어지고 있습니다. 잠시 논점을 정리하고 진행할까요?"
         pass

    # LLM 기반 품질 검사 예시 (프롬프트 예시)
    # quality_prompt = f"""다음 대화 기록을 분석하여 논점 이탈, 불필요한 반복, 또는 비건설적인 부분이 있는지 확인해주세요. 문제가 있다면 간략하게 지적하고 개선 방향을 제안하는 짧은 메시지를 작성해주세요. 문제가 없다면 'None'을 반환하세요.\n\n대화 기록:\n{[m.content for m in messages[-6:]]}""" # 최근 6개 메시지 분석 예시
    # response = await llm_quality_check.ainvoke([SystemMessage(content=quality_prompt)])
    # quality_comment = response.content.strip()
    # if quality_comment.lower() != 'none':
    #    return f"(Moderator 알림) {quality_comment}"

    return None # 특이사항 없을 경우 None 반환

# --- Moderator 노드 함수 ---
async def moderator_node(state: GraphState) -> Dict[str, Any]: # async로 변경 (품질 검사 함수 호출 위해)
    """
    Moderator 노드: /summarize 처리, 토론 품질 관리, 최종 응답 설정 및 메시지 기록 추가
    """
    print("--- Moderator Node 실행 ---")

    # 디버깅 로그: 노드 시작 시 메시지 목록 확인
    messages = state.get('messages', [])
    print(f"Moderator: 노드 시작 시 받은 메시지 목록 (개수: {len(messages)}):")
    for i, msg in enumerate(messages):
        print(f"  [{i}] {type(msg).__name__}: {msg.content[:100]}...")

    flags = state.get('moderator_flags', [])
    last_critic_output = state.get('last_critic_output')
    final_response_content: str | None = None
    error_msg: Optional[str] = None
    quality_comment: Optional[str] = None # 품질 검사 결과 저장 변수

    try:
        # 1. /summarize 명령어 처리 (가장 우선)
        if "summarize_request" in flags:
            print("Moderator: /summarize 요청 처리 중")
            if not llm_fast:
                 error_msg = "요약 기능을 위한 LLM 클라이언트가 로드되지 않았습니다."
                 print(f"Moderator: 오류 - {error_msg}")
                 final_response_content = f"(시스템 오류: {error_msg})"
            elif not messages:
                 print("Moderator: 요약할 메시지가 없습니다.")
                 final_response_content = "**대화 요약:**\n\n요약할 대화 내용이 없습니다."
            else:
                # 요약 프롬프트 (이전과 동일)
                summary_prompt_text = """ ... (이전 상세 프롬프트 내용) ... """

                # 요약 대상 메시지 준비 (/summarize 명령어 제외)
                messages_to_summarize = [
                    msg for msg in messages
                    if not (isinstance(msg, HumanMessage) and msg.content.strip().lower() == '/summarize')
                ]
                print(f"Moderator: /summarize 제외 후 요약 대상 메시지 개수: {len(messages_to_summarize)}")

                if not messages_to_summarize:
                     print("Moderator: /summarize 명령어를 제외하니 요약할 메시지가 없습니다.")
                     final_response_content = "**대화 요약:**\n\n요약할 대화 내용이 없습니다."
                else:
                     summary_messages: List[BaseMessage] = [SystemMessage(content=summary_prompt_text)]
                     summary_messages.extend(messages_to_summarize)
                     print(f"Moderator: 요약 생성 LLM 호출 (메시지 {len(messages_to_summarize)}개 + 시스템 프롬프트 1개)")
                     summary_response = await llm_fast.ainvoke(summary_messages) # 비동기 호출
                     final_response_content = f"**대화 요약:**\n\n{summary_response.content.strip()}"
                     print("Moderator: 요약 생성 완료")

        # 2. 토론 품질 관리 (요약 요청이 없을 때만 실행)
        if not final_response_content: # 아직 최종 응답이 결정되지 않았다면 품질 검사 시도
            print("Moderator: 토론 품질 검사 시도...")
            quality_comment = await check_discussion_quality(messages)
            if quality_comment:
                 print(f"Moderator: 품질 관련 코멘트 생성 - '{quality_comment}'")
                 # 품질 코멘트를 Critic 응답 앞에 추가하거나, 별도 메시지로 전달 가능
                 # 여기서는 Critic 응답이 있을 경우 그 앞에 추가하는 방식 선택
                 pass # 아래 최종 응답 결정 로직에서 처리

        # 3. 최종 응답 결정
        if final_response_content:
            # 요약이 이미 생성된 경우
            print(f"Moderator: 최종 응답 결정됨 (요약) - '{final_response_content[:50]}...'")
            pass # final_response_content 사용
        elif last_critic_output and isinstance(last_critic_output, dict):
            # Critic 노드의 출력을 사용
            critic_comment = last_critic_output.get("comment")
            if not critic_comment:
                 print("Moderator: Critic 출력에서 comment 찾을 수 없음")
                 critic_comment = "(오류: 응답 내용을 찾을 수 없습니다.)"

            # 품질 코멘트가 있다면 Critic 응답 앞에 추가
            if quality_comment:
                final_response_content = f"{quality_comment}\n\n---\n\n{critic_comment}"
                print(f"Moderator: 최종 응답 결정됨 (품질 코멘트 + Critic 출력) - '{final_response_content[:50]}...'")
            else:
                final_response_content = critic_comment
                print(f"Moderator: 최종 응답 결정됨 (Critic 출력) - '{final_response_content[:50]}...'")
        else:
            # Critic 출력도 없고 요약/품질 코멘트도 없는 경우 (오류 상황)
            error_msg = "Moderator: 최종 응답으로 사용할 내용을 찾을 수 없습니다."
            print(error_msg)
            final_response_content = f"(시스템 오류: {error_msg})"


        # 4. 상태 업데이트 준비
        updates = {
            "final_response": final_response_content,
            "moderator_flags": [],  # 처리 후 플래그 초기화
            "error_message": error_msg, # 오류 메시지 설정
             # --- Moderator 메시지 기록 결정 및 추가 ---
             # Moderator가 생성한 최종 응답(요약 또는 품질 코멘트 포함 메시지)을
             # 대화 기록에 AIMessage로 추가합니다.
            "messages": [AIMessage(content=final_response_content if final_response_content else "")]
        }

        return updates

    except Exception as e:
        error_msg = f"Moderator 노드 심각한 오류 발생: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        # 오류 발생 시에도 오류 메시지를 final_response 및 message로 기록
        final_response_content = f"(시스템 오류: {error_msg})"
        return {
            "error_message": error_msg,
            "final_response": final_response_content,
            "messages": [AIMessage(content=final_response_content)]
            }