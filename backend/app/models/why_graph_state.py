# backend/app/models/why_graph_state.py

from typing import List, Optional, Dict, TypedDict, Annotated, Any
from langchain_core.messages import BaseMessage
# Field와 default_factory를 사용하기 위해 pydantic_v1 임포트 (LangGraph 호환성)
from pydantic import Field, BaseModel


class WhyGraphState(TypedDict, total=False):
    """'Why 흐름' 오케스트레이션을 위한 상태 정의"""

    # --- 기본 및 대화 정보 ---
    messages: List[BaseMessage]
    session_id: Optional[str]

    # LangGraph 내부 상태 관리용 필드들
    channel_values: Dict[str, List[BaseMessage]]
    metadata: Dict[str, Any]
    versions_seen: Dict[str, Any]

    # 원본 입력
    raw_topic: Optional[str]
    raw_idea: Optional[str]
    initial_topic: Optional[str]

    # 대화 상태
    has_asked_initial: bool
    # dialogue_history: List[Dict[str, str]] # messages 채널을 주 기록으로 사용하므로 제거 또는 주석 처리 가능
    error_message: Optional[str]

    # 단계별 상태
    idea_summary: Optional[str]
    # identified_what: Optional[str] # 사용되지 않는다면 제거 가능
    # identified_how: Optional[str] # 사용되지 않는다면 제거 가능
    final_motivation_summary: Optional[str]
    motivation_cleared: bool
    identified_assumptions: List[str]
    probed_assumptions: List[str] # 탐색된 가정 목록 (질문 생성 시 추가됨)
    assumptions_fully_probed: bool # 모든 가정이 탐색되었는지 여부
    findings_summary: Optional[str]
    older_history_summary: Optional[str] # 자유 대화용

    # --- 사용자 입력 대기 신호용 키 ---
    clarification_question: Optional[str] # motivation_elicitation 노드가 질문 시 설정
    assumption_question: Optional[str]    # probe_assumption 노드가 질문 시 설정
    # (다른 노드에서 사용자 입력 필요 시 해당 키 추가)

