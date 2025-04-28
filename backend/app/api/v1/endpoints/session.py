# backend/app/api/v1/endpoints/session.py

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ....core import state_manager
from ....models.session import SessionCreateRequest, SessionCreateResponse
from ....models.chat import Message
from ....db.session import get_db_session
from ....core.redis_checkpointer import RedisCheckpointer
from ....core.sql_checkpointer import SQLCheckpointer
from ....core.checkpointers import CombinedCheckpointer
from typing import List

from ....core.config import get_settings

settings = get_settings()

router = APIRouter()

@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새로운 토론 세션 생성",
    tags=["Session Management"],
)
async def create_session(request: SessionCreateRequest):
    """ 새로운 토론 세션 생성 """
    try:
        session_id = state_manager.create_new_session(
            topic=request.topic,
            initial_agent_type=request.initial_agent_type
        )
        print(f"세션 생성됨 (API): {session_id}, 초기 에이전트: {request.initial_agent_type}")
        return SessionCreateResponse(session_id=session_id)
    except Exception as e:
        print(f"세션 생성 오류 (API): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 생성 실패: {e}"
        )

@router.get("/sessions/{session_id}/messages", response_model=List[Message], tags=["Session Management"])
async def get_session_messages(session_id: str, db: AsyncSession = Depends(get_db_session)):
    """ 해당 세션의 메시지 기록을 LangGraph 체크포인터에서 조회하여 반환합니다. """
    print(f"세션 {session_id} 메시지 기록 요청")

    redis_cp = RedisCheckpointer(settings.REDIS_URL, ttl=settings.SESSION_TTL_SECONDS)
    sql_cp = SQLCheckpointer(db)
    checkpointer = CombinedCheckpointer(redis_cp, sql_cp)

    try:
        current_state = await checkpointer.aget(session_id)
        if not current_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"세션 {session_id}에 대한 기록을 찾을 수 없습니다."
            )

        messages_raw = current_state.get("messages", [])
        messages = [
            Message(role=msg.type if hasattr(msg, "type") else "assistant", content=msg.content)
            for msg in messages_raw if isinstance(msg, (HumanMessage, AIMessage))
        ]

        return messages

    except Exception as e:
        print(f"세션 메시지 조회 오류: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메시지 기록 조회 중 오류 발생: {e}"
        )
