# backend/app/api/v1/endpoints/why_explore.py

from fastapi import APIRouter, HTTPException, status, Path, Body
from pydantic import BaseModel, Field
from typing import Optional, Set


# Why 흐름 오케스트레이션 실행 함수 및 상태 모델 임포트
from ....core.why_orchestration import run_why_exploration_turn, app_why_graph
from ....models.chat import MessageResponse
from langchain_core.messages import AIMessage
from langgraph.errors import GraphInterrupt

router = APIRouter()

# 세션별 첫 호출 여부 추적
_first_call_sessions: Set[str] = set()

class WhyExploreRequest(BaseModel):
    initial_idea: str = Field(..., description="Why 탐색을 시작할 초기 아이디어 또는 주제")

@router.post(
    "/sessions/{session_id}/explore-why",
    response_model=MessageResponse,
    summary="'Why 흐름' 탐색 시작 또는 계속",
    tags=["Why Exploration"]
)
async def start_or_continue_why_exploration(
    session_id: str = Path(..., title="Session ID", description="Why 탐색을 진행할 세션 ID"),
    request: WhyExploreRequest = Body(...)
):
    """
    지정된 세션에서 'Why 흐름' 탐색을 시작하거나 계속합니다.

    - **첫 호출:** 초기 아이디어를 기반으로 첫 번째 질문을 생성합니다.
    - **이후 호출:** 이전 상태를 기반으로 다음 질문 또는 최종 결과를 생성합니다.
    """
    print(f"API: '/explore-why' called (Session: {session_id}), Idea: {request.initial_idea}")

    try:
        first_call = session_id not in _first_call_sessions
        if first_call:
            _first_call_sessions.add(session_id)
            # 첫 호출: 전체 플로우 실행하여 상태에 메시지 쌓기
            await run_why_exploration_turn(
                session_id=session_id,
                user_input=request.initial_idea,
                initial_topic=request.initial_idea
            )
            # 체크포인터에서 상태 가져와 첫 AI 질문 추출
            config = {"configurable": {"thread_id": session_id}}
            state = app_why_graph.get_state(config=config)
            msgs = getattr(state, 'values', {}).get('messages', []) or []
            # AIMessage 첫 번째 항목 찾기
            first_ai = None
            for m in msgs:
                if isinstance(m, AIMessage):
                    first_ai = m.content
                    break
            if not first_ai:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="첫 AI 질문을 가져오지 못했습니다. 아이디어를 다시 입력해 주세요."
                )
        else:
            # 이후 호출: 다음 질문 또는 결과 반환
            ai_response_content = await run_why_exploration_turn(
                session_id=session_id,
                user_input=request.initial_idea
            )

        # 오류 반환 처리
        if ai_response_content is None or ai_response_content.startswith("(시스템 오류:"):
            print(f"API: Why 흐름 오류 또는 응답 없음 - {ai_response_content}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ai_response_content or "Why 흐름 처리 중 응답을 받지 못했습니다."
            )

        print("API: Why 흐름 응답 반환")
        return MessageResponse(content=ai_response_content)

    except HTTPException:
        raise
    except GraphInterrupt as gi:
        print(f"GraphInterrupt 발생 - 사용자 입력 요구됨 (Session: {session_id})")
        return MessageResponse(content=str(gi.value))  # 혹은 gi.args[0]
