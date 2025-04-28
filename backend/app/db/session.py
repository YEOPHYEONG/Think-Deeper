from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..core.config import get_settings
from .models import Base

settings = get_settings()  # 인스턴스를 여기서 생성

# 테스트 환경에 DATABASE_URL이 없으면 메모리 SQLite를 사용
engine = create_engine(
    settings.DATABASE_URL or "sqlite:///:memory:",
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db_session():
    return SessionLocal()

Base.metadata.create_all(bind=engine)