# backend/app/models/session.py
from pydantic import BaseModel, Field
from typing import Optional # Optional 임포트

class SessionCreateRequest(BaseModel):
    topic: str = Field(..., description="대화의 초기 주제")
    initial_agent_type: Optional[str] = Field(None, description="초기 대화 대상 에이전트 타입") # 필드 추가

class SessionCreateResponse(BaseModel):
    session_id: str = Field(description="생성된 고유 세션 ID")