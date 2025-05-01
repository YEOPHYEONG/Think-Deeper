# backend/app/models/why_graph_state.py

from typing import List, Optional, Dict, TypedDict, Annotated
from langchain_core.messages import BaseMessage
# Field와 default_factory를 사용하기 위해 pydantic_v1 임포트 (LangGraph 호환성)
from pydantic import Field

# 상태 모델 정의
class WhyGraphState(TypedDict):
    """'Why 흐름' 오케스트레이션을 위한 상태 정의"""

    # --- 기본 및 대화 정보 ---
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    """대화 메시지 기록 (LangGraph 표준 방식)"""

    session_id: Optional[str] = None
    """현재 대화 세션 ID"""

    initial_topic: Optional[str] = None
    """사용자가 제공한 초기 아이디어/주제 원본 또는 요약"""

    error_message: Optional[str] = None
    """노드 실행 중 발생한 오류 메시지 저장"""

    # --- Why 흐름 단계별 상태 ---
    idea_summary: Optional[str] = None
    """understand_idea_node에서 생성된 아이디어 요약"""

    identified_what: Optional[str] = None
    """understand_idea_node에서 식별된 'What'"""

    identified_how: Optional[str] = None
    """understand_idea_node에서 식별된 'How'"""

    final_motivation_summary: Optional[str] = None
    """clarify_motivation_node에서 동기가 명확하다고 판단했을 때 생성된 최종 동기 요약"""

    motivation_clear: bool = False
    """clarify_motivation_node에서 동기가 명확하다고 판단했는지 여부 (라우팅에 사용)"""

    identified_assumptions: List[str] = Field(default_factory=list)
    """identify_assumptions_node에서 식별 및 중요도 순으로 정렬된 가정 목록"""

    probed_assumptions: List[str] = Field(default_factory=list)
    """probe_assumption_node에서 이미 질문한 가정 목록 (중복 질문 방지용)"""

    assumptions_fully_probed: bool = False
    """probe_assumption_node에서 모든 가정을 탐색했다고 판단했는지 여부 (라우팅에 사용)"""