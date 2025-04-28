# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.api import api_router_v1
from .core.config import get_settings

# 설정 불러오기
settings = get_settings()

# FastAPI 앱 생성
app = FastAPI(
    title="Think Deeper API",
    description="AI 기반 다각적 사고 증진 서비스 'Think Deeper'의 API입니다.",
    version="0.1.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 루트 엔드포인트
@app.get("/", tags=["Root"])
async def read_root():
    keys_loaded_status = {
        "openai": settings.OPENAI_API_KEY is not None,
        "anthropic": settings.ANTHROPIC_API_KEY is not None,
        "gemini": settings.GEMINI_API_KEY is not None,
        "tavily": settings.TAVILY_API_KEY is not None,
    }
    return {
        "message": "Welcome to the Think Deeper API!",
        "status": "running",
        "docs_url": "/docs",
        "loaded_api_keys": keys_loaded_status,
    }

# API v1 라우터 추가
app.include_router(api_router_v1, prefix="/api/v1")
