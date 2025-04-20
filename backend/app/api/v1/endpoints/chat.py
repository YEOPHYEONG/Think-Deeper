# backend/app/api/v1/endpoints/chat.py
from fastapi import APIRouter, HTTPException, status, Path
# 경로를 조정하여 core 및 models 모듈 임포트
from ....core import orchestration
from ....models.chat import SendMessageRequest, MessageResponse

router = APIRouter()

@router.post(
    "/sessions/{session_id}/message", # 경로 파라미터로 session_id 받음
    response_model=MessageResponse, # 응답 데이터 모델
    summary="세션에 메시지 전송 및 Critic 응답 받기", # API 문서용 요약
    tags=["Chat"] # API 문서용 태그
)
async def send_message(
    request: SendMessageRequest, # 요청 본문 모델
    session_id: str = Path(..., title="Session ID", description="메시지를 보낼 세션의 ID") # 경로 파라미터 정의
):
    """
    지정된 세션 ID에 사용자 메시지를 전송하고,
    백엔드 오케스트레이션 로직을 실행하여 Critic 에이전트의 응답을 받아 반환합니다.
    (첫 번째 메시지일 경우, 세션 생성 시 입력된 주제가 사용될 수 있음)
    """
    print(f"API: 세션 {session_id}에 메시지 수신: '{request.content}'")
    try:
        # 핵심 오케스트레이션 함수 호출 (비동기)
        critic_response = await orchestration.run_conversation_turn(
            session_id,
            request.content
        )

        # 오케스트레이션 결과 확인 (오류 처리)
        if critic_response is None or critic_response.startswith("오류:") or critic_response.startswith("Error:"):
            print(f"API: 세션 {session_id} 오케스트레이션 오류: {critic_response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=critic_response or "오케스트레이션 처리 중 응답을 받지 못했습니다."
            )

        print(f"API: 세션 {session_id}에 대한 Critic 응답 전송")
        # 성공 시 Critic 응답 반환
        return MessageResponse(content=critic_response)

    except HTTPException as http_exc:
        # 이미 HTTP 예외인 경우 그대로 다시 발생시킴
        raise http_exc
    except Exception as e:
        # 그 외 예외 처리
        print(f"API 오류: 세션 {session_id} 메시지 처리 실패 - {e}")
        import traceback
        traceback.print_exc() # 디버깅용 스택 트레이스 출력
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메시지 처리에 실패했습니다: {e}"
        )