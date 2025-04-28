# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# 나중에 API 라우터를 추가할 것입니다.
from .api.v1.api import api_router_v1
from .core.config import get_settings # 설정 로드 함수 임포트
from .db.models import Base  # SQLAlchemy declarative_base
from .db.session import engine

# FastAPI 앱이 시작될 때 설정을 로드합니다.
settings = get_settings()

app = FastAPI(
    title="Think Deeper API",
    description="AI 기반 다각적 사고 증진 서비스 'Think Deeper'의 API입니다.",
    version="0.1.0"
    # 필요한 경우 다른 FastAPI 설정 추가 가능
)

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Root"])
async def read_root():
    """루트 경로, API 상태 확인 및 문서 링크 제공."""
    keys_loaded_status = {
        "openai": settings.OPENAI_API_KEY is not None,
        "anthropic": settings.ANTHROPIC_API_KEY is not None,
        "gemini": settings.GEMINI_API_KEY is not None,
        "tavily": settings.TAVILY_API_KEY is not None, # Tavily 키 확인 추가
    }
    return {
        "message": "Welcome to the Think Deeper API!",
        "status": "running",
        "docs_url": "/docs", # API 문서 경로 안내 추가
        "loaded_api_keys": keys_loaded_status
    }

# --- v1 API 라우터 포함 ---
# /api/v1 경로 아래에 v1 라우터의 모든 엔드포인트를 추가합니다.
app.include_router(api_router_v1, prefix="/api/v1")
# --- -------------- ---
# 필요시 애플리케이션 시작/종료 이벤트 핸들러 추가
# @app.on_event("startup")
# async def on_startup():
#     print("서버 시작됨...")

# @app.on_event("shutdown")
# async def on_shutdown():
#     print("서버 종료됨...")