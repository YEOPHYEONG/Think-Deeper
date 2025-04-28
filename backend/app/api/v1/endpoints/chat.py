# backend/app/api/v1/endpoints/chat.py

from fastapi import APIRouter, HTTPException, status, Path, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.orchestration import run_conversation_turn_langgraph
from ....models.chat import SendMessageRequest, MessageResponse
from ....db.session import get_db_session

router = APIRouter()

@router.post(
    "/sessions/{session_id}/message",
    response_model=MessageResponse,
    summary="세션에 메시지 전송 및 Critic 응답 받기",
    tags=["Chat"]
)
async def send_message(
    request: SendMessageRequest,
    session_id: str = Path(..., title="Session ID", description="메시지를 보낼 세션의 ID"),
    db: AsyncSession = Depends(get_db_session),  # ✅ 비동기 세션 주입
):
    """
    세션에 메시지를 전송하고 Critic의 응답을 받아 반환합니다.
    """
    print(f"API: 세션 {session_id}에 메시지 수신: '{request.content}'")

    try:
        critic_response = await run_conversation_turn_langgraph(
            session_id,
            request.content
        )

        if critic_response is None or critic_response.startswith("오류:") or critic_response.startswith("Error:"):
            print(f"API: 세션 {session_id} 오케스트레이션 오류: {critic_response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=critic_response or "오케스트레이션 처리 중 응답을 받지 못했습니다."
            )

        print(f"API: 세션 {session_id}에 대한 Critic 응답 전송")
        return MessageResponse(content=critic_response)

    except HTTPException:
        raise
    except Exception as e:
        print(f"API 오류: 세션 {session_id} 메시지 처리 실패 - {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메시지 처리에 실패했습니다: {e}"
        )
