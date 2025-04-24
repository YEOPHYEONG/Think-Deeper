# backend/app/models/graph_state.py
from typing import List, Optional, Dict, TypedDict, Annotated
from langchain_core.messages import BaseMessage
# from langchain_core.documents import Document # 검색 결과 타입 (필요시)

# 검색 결과 타입을 간단히 정의 (필요시 langchain_core.documents.Document 사용)
class SearchResult(TypedDict):
    title: str
    url: str
    content: str

class GraphState(TypedDict):
    """Think Deeper 서비스의 LangGraph 상태 정의"""

    # 대화 기록 (LangChain 메시지 객체 리스트)
    messages: Annotated[List[BaseMessage], lambda x, y: x + y] # 새 메시지를 기존 리스트에 추가

    # 현재 모드 ("Standard" 또는 "FastDebate")
    mode: str

    # 표준 모드 뉘앙스 ("Debate" 또는 "Discussion")
    nuance: Optional[str] # 빠른 모드에서는 None일 수 있음

    # Critique-Depth 슬라이더 값 (0-100)
    critique_depth: int

    # 현재 턴의 논의 초점 (점진적 대화를 위해)
    current_focus: Optional[str]

    # Critic이 요청한 검색 쿼리
    search_query: Optional[str]

    # Search Agent가 반환한 검색 결과
    search_results: Optional[List[SearchResult]] # Document 타입 사용 고려

    # 가장 최근 Critic의 구조화된 출력 (Moderator 검토용)
    # 구체적인 구조는 Critic 구현에 따라 달라짐 (예: Dict)
    last_critic_output: Optional[Dict]

    # Moderator 개입 플래그 (예: 'summarize_request', 'off_topic_warning')
    moderator_flags: List[str]

    # 최종 사용자에게 전달될 응답
    final_response: Optional[str]

    # (추가 고려) 세션 정보
    session_id: str
    initial_topic: str

    # (추가 고려) 오류 정보
    error_message: Optional[str]
