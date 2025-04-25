# backend/app/models/graph_state.py
from typing import List, Optional, Dict, TypedDict, Annotated
from langchain_core.messages import BaseMessage

class SearchResult(TypedDict):
    title: str
    url: str
    content: str

class GraphState(TypedDict):
    """Think Deeper 서비스의 LangGraph 상태 정의"""
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    mode: str # 예: "Standard", "FastDebate", "OneOnOne" 등
    nuance: Optional[str] # 예: "Debate", "Discussion"
    critique_depth: int
    current_focus: Optional[str]
    search_query: Optional[str]
    search_results: Optional[List[SearchResult]]
    last_critic_output: Optional[Dict]
    # --- 신규 에이전트 출력 필드 (선택적) ---
    last_advocate_output: Optional[Dict]
    last_why_output: Optional[Dict]
    last_socratic_output: Optional[Dict]
    # --- ---
    moderator_flags: List[str]
    final_response: Optional[str]
    # --- 세션 및 타겟 에이전트 정보 추가 ---
    session_id: str # 세션 식별자
    initial_topic: str # 초기 주제
    target_agent: Optional[str] # 현재 1:1 대화 대상 에이전트
    # --- ---
    error_message: Optional[str]