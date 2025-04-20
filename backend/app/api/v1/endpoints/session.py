# backend/app/api/v1/endpoints/session.py
from fastapi import APIRouter, HTTPException, status
# 경로를 조정하여 core 및 models 모듈 임포트
from ....core import state_manager
from ....models.session import SessionCreateRequest, SessionCreateResponse

router = APIRouter()

@router.post(
    "/sessions", # 엔드포인트 경로
    response_model=SessionCreateResponse, # 응답 데이터 모델
    status_code=status.HTTP_201_CREATED, # 성공 시 상태 코드
    summary="새로운 토론/토의 세션 생성", # API 문서용 요약
    tags=["Session Management"] # API 문서용 태그
)
async def create_session(request: SessionCreateRequest):
    """
    초기 주제를 받아 새로운 대화 세션을 시작합니다.
    상태 관리자에 세션 정보를 초기화하고 고유 세션 ID를 반환합니다.
    """
    try:
        # 상태 관리자를 호출하여 새 세션 생성 및 ID 받기
        session_id = state_manager.create_new_session(topic=request.topic)
        print(f"API: 새 세션 생성됨 - ID: {session_id}")
        # 성공 응답 반환
        return SessionCreateResponse(session_id=session_id)
    except Exception as e:
        # 오류 발생 시 로깅 및 HTTP 오류 응답
        print(f"API 오류: 세션 생성 실패 - {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 생성에 실패했습니다: {e}"
        )