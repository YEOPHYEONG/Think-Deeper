# backend/app/graph_nodes/search.py
from typing import Dict, Any, List, Optional
from tavily import TavilyClient

from ..models.graph_state import GraphState, SearchResult
from ..core.config import get_settings # 설정 로드 (API 키 등)

settings = get_settings()

# Tavily 클라이언트 초기화
tavily_client: Optional[TavilyClient] = None
if settings.TAVILY_API_KEY:
    try:
        tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        print("Search Node: Tavily 클라이언트 초기화 성공.")
    except Exception as e:
        print(f"Search Node: Tavily 클라이언트 초기화 오류: {e}")
else:
    print("Search Node: 경고 - TAVILY_API_KEY가 설정되지 않아 웹 검색 불가.")


def search_node(state: GraphState) -> Dict[str, Any]:
    """
    Search 노드: Critic이 요청한 쿼리로 웹 검색(Tavily)을 수행하고
    결과를 GraphState 형식에 맞게 반환합니다.
    """
    print("--- Search Node 실행 ---")

    query = state.get('search_query')
    results: List[SearchResult] = []
    error_msg: Optional[str] = None

    if not query:
        error_msg = "Search Node: 검색 쿼리가 없습니다."
        print(error_msg)
    elif not tavily_client:
        error_msg = "Search Node: Tavily 클라이언트가 초기화되지 않았습니다."
        print(error_msg)
    else:
        try:
            print(f"Search: Tavily 검색 수행 - '{query}'")
            # Tavily 검색 API 호출 (기존 tools/search.py 로직 참고)
            response = tavily_client.search(
                query=query,
                search_depth="basic",  # 또는 'advanced'
                include_answer=False,
                max_results=3
            )

            # 결과 파싱 및 GraphState 형식으로 변환
            tavily_results = response.get('results', [])
            if tavily_results:
                for res in tavily_results:
                    results.append({
                        "title": res.get('title', 'N/A'),
                        "url": res.get('url', 'N/A'),
                        "content": res.get('content', 'N/A') # Tavily의 content는 스니펫/요약
                    })
                print(f"Search: 검색 성공 - {len(results)}개 결과 반환.")
            else:
                print(f"Search: '{query}'에 대한 검색 결과 없음.")
                # 결과 없음을 상태에 반영할 수도 있음

        except Exception as e:
            error_msg = f"Search Node: Tavily 검색 중 오류 발생 - {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()

    # 상태 업데이트 반환
    updates = {
        "search_results": results,
        "search_query": None,  # 처리 후 쿼리 초기화
        "error_message": error_msg
    }
    print(f"Search: 상태 업데이트 반환 - Results: {len(results)}개, Error: {error_msg}")
    return updates