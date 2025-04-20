# backend/app/tools/search.py
import os
from tavily import TavilyClient
# core.config에서 설정 로드 함수를 가져옵니다. (상대 경로 주의)
from ..core.config import get_settings
from typing import List, Dict, Any

# 설정 로드 (API 키 포함)
settings = get_settings()
tavily_client = None

# Tavily 클라이언트 초기화 (API 키가 설정된 경우에만)
if settings.TAVILY_API_KEY:
    try:
        # TavilyClient 초기화 시 API 키 전달
        tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        print("Tavily 클라이언트 초기화 성공.")
    except Exception as e:
        print(f"Tavily 클라이언트 초기화 오류: {e}")
        tavily_client = None
else:
    print("경고: TAVILY_API_KEY가 .env 파일 또는 환경 변수에 설정되지 않았습니다. 웹 검색 도구가 작동하지 않습니다.")

def web_search(query: str) -> str:
    """
    주어진 쿼리를 사용하여 Tavily API로 웹 검색을 수행하고,
    결과를 요약하여 문자열로 반환합니다.

    Args:
        query (str): 검색할 쿼리 문자열.

    Returns:
        str: 검색 결과 요약 문자열 또는 오류 메시지.
    """
    if not tavily_client:
        return "오류: Tavily API 키가 설정되지 않았거나 클라이언트 초기화에 실패했습니다."

    print(f"웹 검색 수행 (Tavily): '{query}'")
    try:
        # Tavily 검색 API 호출
        response = tavily_client.search(
            query=query,
            search_depth="basic",  # 검색 깊이: 'basic' 또는 'advanced'
            include_answer=False, # LLM 답변 요약 포함 여부 (우선 False)
            max_results=3         # 최대 결과 수
        )

        # 결과 처리 및 포맷팅
        results = response.get('results', [])
        if not results:
            return f"'{query}'에 대한 검색 결과가 없습니다."

        # 결과를 하나의 문자열로 조합
        formatted_results = f"'{query}'에 대한 검색 결과:\n\n"
        for i, result in enumerate(results):
            formatted_results += f"결과 {i+1}:\n"
            formatted_results += f"  제목: {result.get('title', 'N/A')}\n"
            formatted_results += f"  URL: {result.get('url', 'N/A')}\n"
            # Tavily 결과의 'content'는 보통 요약이나 스니펫입니다.
            formatted_results += f"  내용: {result.get('content', 'N/A')}\n\n"

        print(f"검색 성공. {len(results)}개 결과 반환.")
        return formatted_results.strip()

    except Exception as e:
        print(f"Tavily 검색 중 오류 발생: {e}")
        return f"'{query}' 웹 검색 중 오류 발생: {e}"

# --- 이 파일을 직접 실행하여 테스트할 경우를 위한 부분 (주석 처리됨) ---
# async def main():
#      # ... 테스트 로직 ...
# if __name__ == "__main__":
#      # import asyncio
#      # asyncio.run(main())
#      pass