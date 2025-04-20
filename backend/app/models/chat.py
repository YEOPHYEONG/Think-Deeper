# backend/app/models/chat.py
from pydantic import BaseModel, Field
from typing import List, Literal
# from datetime import datetime # 필요시 타임스탬프용

# 역할 정의: 사용자 또는 어시스턴트(Critic)
Role = Literal["user", "assistant"]

class ChatMessage(BaseModel):
    """단일 채팅 메시지를 나타내는 모델"""
    role: Role
    content: str
    # timestamp: datetime = Field(default_factory=datetime.utcnow) # 선택사항: 필요시 타임스탬프 추가

class ConversationHistory(BaseModel):
     """대화 기록 전체를 나타내는 모델 (메시지 리스트)"""
     messages: List[ChatMessage] = []

class SendMessageRequest(BaseModel):
    """세션 내에서 사용자가 새 메시지를 보낼 때의 요청 모델"""
    content: str

class MessageResponse(BaseModel):
    """어시스턴트(Critic)의 응답 메시지 모델"""
    role: Literal["assistant"] = "assistant" # 응답 역할은 항상 assistant
    content: str