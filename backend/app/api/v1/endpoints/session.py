# backend/app/api/v1/endpoints/session.py

from fastapi import APIRouter, HTTPException, status
from ....core import state_manager
from ....models.session import SessionCreateRequest, SessionCreateResponse

router = APIRouter()

# 1) 전역 메시지 스토어
#    세션ID → List[{"role":..., "content":...}]
SESSION_STORE: dict[str, list[dict]] = {}

@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새로운 토론 세션 생성",
    tags=["Session Management"],
)
async def create_session(request: SessionCreateRequest):
    try:
        session_id = state_manager.create_new_session(topic=request.topic)
        # 메시지 히스토리 초기화
        SESSION_STORE[session_id] = []
        return SessionCreateResponse(session_id=session_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 생성 실패: {e}"
        )

@router.get("/sessions/{session_id}/messages", tags=["Session Management"])
async def get_session_messages(session_id: str):
    return SESSION_STORE.get(session_id, [])
