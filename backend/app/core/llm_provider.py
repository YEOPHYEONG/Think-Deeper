# backend/app/core/llm_provider.py
# from langchain_google_genai import ChatGoogleGenerativeAI # 필요시 유지
from langchain_openai import ChatOpenAI # OpenAI 클라이언트 임포트
# from langchain_anthropic import ChatAnthropic
from functools import lru_cache
from .config import get_settings

settings = get_settings()

@lru_cache()
def get_llm_client(provider: str = "openai", model_name: str = "gpt-4o", temperature: float = 0.7): # 기본 provider/model 변경
    """지정된 제공자와 모델명으로 LLM 클라이언트를 생성하여 반환"""
    print(f"LLM 클라이언트 요청: Provider={provider}, Model={model_name}, Temp={temperature}")

    if provider == "google":
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI # 함수 내에서 임포트 가능
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=settings.GEMINI_API_KEY,
                convert_system_message_to_human=True,
                temperature=temperature,
            )
        except Exception as e:
            print(f"Gemini 클라이언트 ({model_name}) 생성 실패: {e}")
            raise

    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        try:
            # 사용자가 제공한 OpenAI 모델명 사용 가능
            # 예: "gpt-4o", "gpt-4o-mini", "gpt-4-turbo" 등
            return ChatOpenAI(model=model_name, api_key=settings.OPENAI_API_KEY, temperature=temperature)
        except Exception as e:
            print(f"OpenAI 클라이언트 ({model_name}) 생성 실패: {e}")
            raise

    # elif provider == "anthropic":
    #     ... (Anthropic 로직)

    else:
        raise ValueError(f"지원하지 않는 LLM 제공자입니다: {provider}")

# --- 기본 제공 함수 수정 (OpenAI 모델 사용) ---
def get_high_performance_llm():
    """ 기본 고성능 LLM 반환 (예: GPT-4o) """
    # 원하는 OpenAI 모델명으로 변경 (예: "gpt-4o", "gpt-4-turbo")
    return get_llm_client(provider="openai", model_name="gpt-4.1-2025-04-14", temperature=0.7)

def get_fast_llm():
    """ 기본 빠른 LLM 반환 (예: GPT-4o Mini) """
    # 원하는 OpenAI 모델명으로 변경 (예: "gpt-4o-mini")
    return get_llm_client(provider="openai", model_name="gpt-4.1-mini-2025-04-14", temperature=0.7)

def get_focus_llm():
     """ 포커스 결정 등 간단한 작업용 LLM (가장 빠르고 저렴한 모델 권장) """
     # 예: GPT-4o Mini 재사용 또는 더 경량 모델 (예: "gpt-3.5-turbo" 등)
     return get_llm_client(provider="openai", model_name="gpt-4o-mini", temperature=0.2)