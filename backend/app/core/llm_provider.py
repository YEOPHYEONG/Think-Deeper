# backend/app/core/llm_provider.py
from langchain_google_genai import ChatGoogleGenerativeAI
# 필요시 다른 LLM 제공 업체 임포트 (예: langchain_openai, langchain_anthropic)
from functools import lru_cache
from .config import get_settings # 설정 로드

settings = get_settings()

# lru_cache를 사용하면 동일한 설정의 클라이언트를 반복 생성하지 않음
@lru_cache()
def get_llm_client(provider: str = "google", model_name: str = "gemini-1.5-flash-latest", temperature: float = 0.7):
    """지정된 제공자와 모델명으로 LLM 클라이언트를 생성하여 반환"""
    print(f"LLM 클라이언트 요청: Provider={provider}, Model={model_name}, Temp={temperature}") # 로깅 추가

    if provider == "google":
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
        try:
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=settings.GEMINI_API_KEY,
                convert_system_message_to_human=True, # 필요시 사용
                temperature=temperature
            )
        except Exception as e:
            print(f"Gemini 클라이언트 생성 실패: {e}")
            raise # 오류 다시 발생시켜 호출한 쪽에서 처리하도록 함

    # --- 필요시 다른 LLM 제공 업체 지원 추가 ---
    # elif provider == "openai":
    #     if not settings.OPENAI_API_KEY:
    #         raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    #     from langchain_openai import ChatOpenAI
    #     return ChatOpenAI(model=model_name, api_key=settings.OPENAI_API_KEY, temperature=temperature)
    #
    # elif provider == "anthropic":
    #      if not settings.ANTHROPIC_API_KEY:
    #          raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
    #      from langchain_anthropic import ChatAnthropic
    #      # Anthropic 모델 이름 확인 필요 (예: "claude-3-sonnet-20240229")
    #      # return ChatAnthropic(model=model_name, api_key=settings.ANTHROPIC_API_KEY, temperature=temperature)
    #      pass # Anthropic 구현 예시

    else:
        raise ValueError(f"지원하지 않는 LLM 제공자입니다: {provider}")

# --- 편의 함수 (선택 사항) ---
def get_high_performance_llm():
    # 예시: 기본 고성능 모델로 Gemini Pro 사용
    return get_llm_client(provider="google", model_name="gemini-2.5-pro-exp-03-25", temperature=0.7)
def get_fast_llm():
    # 예시: 기본 빠른 모델로 Gemini Flash 사용
    return get_llm_client(provider="google", model_name="gemini-2.5-pro-exp-03-25", temperature=0.7)

def get_focus_llm():
     """ 포커스 결정 등 간단한 작업용 LLM (가장 빠르고 저렴한 모델 권장) """
     # Flash 모델 재사용 또는 더 경량 모델 고려
     # 모델명은 사용 가능한 것으로 변경 필요
     return get_llm_client(provider="google", model_name="gemini-1.5-flash-latest", temperature=0.2)
