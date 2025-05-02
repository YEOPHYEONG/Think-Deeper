# backend/app/api/v1/endpoints/session.py

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi import Body
from sqlalchemy.ext.asyncio import AsyncSession
from ....core import state_manager
from ....models.session import SessionCreateRequest, SessionCreateResponse
from ....models.chat import Message
from ....db.session import get_db_session, async_session_factory
from ....core.redis_checkpointer import RedisCheckpointer
from ....core.sql_checkpointer import SQLCheckpointer
from ....core.checkpointers import CombinedCheckpointer
from app.core.why_orchestration import run_why_exploration_turn
from app.core.recovery_manager import restore_session_to_redis
from typing import List
from langchain_core.messages import HumanMessage, AIMessage
from ....core.config import get_settings
from pydantic import BaseModel
from typing import Optional

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
        # ✅ 비동기로 호출
        session_id = await state_manager.create_new_session(
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

    redis_cp = RedisCheckpointer(settings.REDIS_URL, ttl=settings.SESSION_TTL_SECONDS)  # ✅ 빠졌던 부분 추가
    sql_cp = SQLCheckpointer(async_session_factory)
    checkpointer = CombinedCheckpointer(redis_cp, sql_cp)

    config = {"configurable": {"thread_id": session_id}}  # ✅ 필수
    try:
        current_state = await checkpointer.aget(config)   # ✅ 문자열 넘기던 부분 제거
        if not current_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"세션 {session_id}에 대한 기록을 찾을 수 없습니다."
            )

        messages_raw = current_state.get("messages", [])
        messages = []
        for msg in messages_raw:
            if isinstance(msg, (HumanMessage, AIMessage)):
                messages.append(
                    Message(role=msg.type, content=msg.content)
                )
            elif isinstance(msg, dict):
                messages.append(
                    Message(role=msg.get("sender", "assistant"), content=msg.get("content", ""))
                )

        return messages

    except Exception as e:
        print(f"세션 메시지 조회 오류: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메시지 기록 조회 중 오류 발생: {e}"
        )

@router.post("/sessions/{session_id}/restore")
async def restore_session(session_id: str):
    success = await restore_session_to_redis(session_id)
    if success:
        return {"success": True, "message": "세션 복구 성공"}
    else:
        return {"success": False, "message": "세션 복구 실패"}

class WhyTurnRequest(BaseModel):
    input: Optional[str] = None

@router.post("/sessions/{session_id}/why", tags=["Why Agent"])
async def run_why_turn(session_id: str, req: WhyTurnRequest = Body(...)):
    """ Why agent를 통한 탐색 수행 """
    response = await run_why_exploration_turn(
        session_id=session_id,
        user_input=req.input
    )
    return {"response": response}
