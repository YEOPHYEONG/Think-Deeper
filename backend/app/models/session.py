# backend/app/models/session.py
from pydantic import BaseModel, Field
import uuid # 세션 ID 생성을 위해 추가

class SessionCreateRequest(BaseModel):
    """새 대화 세션 생성을 위한 요청 모델"""
    topic: str = Field(..., description="대화의 초기 주제")

class SessionCreateResponse(BaseModel):
    """새 대화 세션 생성 후 응답 모델"""
    session_id: str = Field(description="생성된 고유 세션 ID")
    # 초기 메시지를 포함할 수도 있음 (선택 사항)
    # initial_message: MessageResponse | None = None