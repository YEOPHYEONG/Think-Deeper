# backend/app/api/v1/api.py
from fastapi import APIRouter
# endpoints 폴더의 라우터들을 임포트
from .endpoints import session, chat
from .endpoints import why_explore # 새로 추가된 라우터 임포트

# v1 API를 위한 메인 라우터 생성
api_router_v1 = APIRouter()

# 각 엔드포인트 라우터를 메인 라우터에 포함
# prefix를 비우면 /api/v1/sessions, /api/v1/sessions/{session_id}/message 경로가 됨
api_router_v1.include_router(session.router, prefix="", tags=["Session Management"])
api_router_v1.include_router(chat.router, prefix="", tags=["Chat"])
api_router_v1.include_router(why_explore.router, prefix="", tags=["Why Exploration"])

# 나중에 다른 엔드포인트 그룹이 추가되면 여기에 포함
# 예: api_router_v1.include_router(user.router, prefix="/users", tags=["User Management"])