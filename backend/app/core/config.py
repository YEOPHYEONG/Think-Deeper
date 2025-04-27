# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict # SettingsConfigDict 임포트 추가
from functools import lru_cache # 설정 객체를 한 번만 로드하기 위해 사용
from typing import Optional

class Settings(BaseSettings):
    # 로드할 환경 변수 정의
    OPENAI_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None # Tavily 키 추가
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None
    SESSION_TTL_SECONDS: int = 3600

    # .env 파일을 읽도록 설정하고, 환경에 없는 변수는 무시합니다.
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    # --- 여기까지 ---


    # 만약 로컬 개발 시 .env 파일을 사용하려면 아래 주석 해제
    # model_config = SettingsConfigDict(env_file='.env', extra='ignore')

# @lru_cache 데코레이터를 사용하면 get_settings() 함수가 처음 호출될 때
# Settings() 인스턴스를 생성하고 그 결과를 캐싱하여, 이후 호출 시에는
# 다시 로드하지 않고 캐시된 인스턴스를 반환합니다. (싱글톤 패턴)
@lru_cache()
def get_settings() -> Settings:
    print("애플리케이션 설정 로딩...") # 디버깅용 로그
    return Settings()

# 이제 다른 파일에서 `from .core.config import get_settings` 로 불러온 후
# `settings = get_settings()` 와 같이 사용하여 설정 객체에 접근할 수 있습니다.