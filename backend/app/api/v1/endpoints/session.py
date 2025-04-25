# backend/app/api/v1/endpoints/session.py
from fastapi import APIRouter, HTTPException, status
from ....core import state_manager # state_manager 임포트 유지 (초기 정보 저장용)
from ....models.session import SessionCreateRequest, SessionCreateResponse
from ....models.chat import Message # Message 모델 임포트 (get_session_messages 응답용)
from typing import List

router = APIRouter()

# TODO: 이 전역 스토어는 LangGraph 체크포인트에서 메시지 기록을 가져오도록 대체해야 함.
SESSION_MESSAGE_STORE: dict[str, list[dict]] = {}

@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새로운 토론 세션 생성",
    tags=["Session Management"],
)
async def create_session(request: SessionCreateRequest):
    """ 새로운 토론 세션을 생성하고 초기 에이전트 타입을 설정합니다. """
    try:
        # state_manager에 초기 정보 저장 요청
        session_id = state_manager.create_new_session(
            topic=request.topic,
            initial_agent_type=request.initial_agent_type
        )
        # TODO: 메시지 스토어 초기화 부분은 LangGraph 체크포인트 설정으로 대체 필요
        SESSION_MESSAGE_STORE[session_id] = []
        print(f"세션 생성됨 (API): {session_id}, 초기 에이전트: {request.initial_agent_type}")
        return SessionCreateResponse(session_id=session_id)
    except Exception as e:
        print(f"세션 생성 오류 (API): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 생성 실패: {e}"
        )

# TODO: 이 엔드포인트는 LangGraph 체크포인트에서 메시지 기록을 가져오도록 수정 필요
@router.get("/sessions/{session_id}/messages", response_model=List[Message], tags=["Session Management"])
async def get_session_messages(session_id: str):
    """
    해당 세션의 메시지 기록을 반환합니다. (임시 구현 - LangGraph 상태 미반영)
    """
    print(f"세션 {session_id} 메시지 기록 요청 (임시 저장소)")
    # 임시 저장소에서 가져옴 (실제 대화와 다를 수 있음)
    # Message 모델 형태로 변환하여 반환
    messages_raw = SESSION_MESSAGE_STORE.get(session_id, [])
    messages = [Message(role=msg.get("role", "assistant"), content=msg.get("content", "")) for msg in messages_raw if msg.get("role") in ["user", "assistant"]]
    return messages