# backend/app/db/session.py
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

# Async 엔진
engine = create_async_engine(settings.DATABASE_URL, future=True)

# AsyncSession 공장
async_session_factory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
)

# 편리한 컨텍스트매니저
@asynccontextmanager
async def get_db_session():
    async with async_session_factory() as session:
        yield session

# 별칭으로도 내보내기 (Async 세션 팩토리)
get_db_session_async = get_db_session
