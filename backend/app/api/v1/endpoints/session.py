# backend/app/api/v1/endpoints/session.py

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi import Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Union # Union 추가

# --- 상대 경로 임포트 수정 ---
# 가정: 현재 파일 위치는 backend/app/api/v1/endpoints/session.py
# core, models, db 등은 app 폴더 하위에 있다고 가정
from ....core import state_manager # state_manager.py 구현 필요
from ....models.session import SessionCreateRequest, SessionCreateResponse
from ....models.chat import Message, MessageResponse # 사용자 정의 모델
from ....db.session import get_db_session, async_session_factory
from ....core.redis_checkpointer import RedisCheckpointer
from ....core.sql_checkpointer import SQLCheckpointer
from ....core.checkpointers import CombinedCheckpointer
from ....core.why_orchestration import run_why_exploration_turn
from ....core.recovery_manager import restore_session_to_redis # recovery_manager.py 구현 필요
from ....core.config import get_settings
# --- Langchain/Langgraph 관련 임포트 ---
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.errors import GraphInterrupt
# --- Pydantic ---
from pydantic import BaseModel

settings = get_settings()

router = APIRouter()

@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새로운 토론 세션 생성",
    tags=["Session Management"],
)
async def create_session(request: SessionCreateRequest):
    """ 새로운 토론 세션 생성 """
    try:
        # state_manager.create_new_session이 초기 상태를 Redis/SQL에 저장한다고 가정
        # 이 초기 상태는 CombinedCheckpointer가 읽을 수 있는 형식이어야 함
        # (예: messages 키를 포함한 빈 리스트)
        print(f"[API /sessions] 요청 수신: Topic='{request.topic}', Agent='{request.initial_agent_type}'")
        session_id = await state_manager.create_new_session(
            topic=request.topic,
            initial_agent_type=request.initial_agent_type
        )
        print(f"[API /sessions] 세션 생성됨: ID={session_id}, 초기 에이전트={request.initial_agent_type}")
        return SessionCreateResponse(session_id=session_id)
    except Exception as e:
        print(f"[API /sessions] 세션 생성 오류: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세션 생성 중 예기치 않은 오류 발생: {e}"
        )

@router.get("/sessions/{session_id}/messages", response_model=List[Message], tags=["Session Management"])
async def get_session_messages(session_id: str, db: AsyncSession = Depends(get_db_session)):
    """ 특정 세션의 메시지 기록 조회 """
    print(f"[API /messages] 세션 {session_id} 메시지 기록 요청")

    # 체크포인터 초기화
    try:
        redis_cp = RedisCheckpointer(settings.REDIS_URL, ttl=settings.SESSION_TTL_SECONDS)
        sql_cp = SQLCheckpointer(async_session_factory)
        checkpointer = CombinedCheckpointer(redis_cp, sql_cp)
    except Exception as e_cp_init:
         print(f"[API /messages] 체크포인터 초기화 오류: {e_cp_init}")
         raise HTTPException(status_code=500, detail="서버 설정 오류")


    config = {"configurable": {"thread_id": session_id}}

    try:
        # aget_user_visible_messages는 이제 항상 리스트를 반환 (비어 있을 수 있음)
        messages_raw: List[Union[BaseMessage, dict]] = await checkpointer.aget_user_visible_messages(config)

        # 메시지 객체를 API 응답 모델로 변환
        processed_messages = []
        for msg_data in messages_raw: # messages_raw는 이제 항상 리스트
            role = "assistant" # 기본값
            content = ""
            try:
                if isinstance(msg_data, HumanMessage):
                    role = "user"
                    content = msg_data.content
                elif isinstance(msg_data, AIMessage):
                    role = "assistant"
                    content = msg_data.content
                elif isinstance(msg_data, dict): # 직렬화된 dict 형태 처리
                    role = msg_data.get("type", "assistant") # 'type'을 role로 사용
                    if role == "ai": role = "assistant" # 'ai'를 'assistant'로 통일
                    content = msg_data.get("content", "")
                else:
                    print(f"  [API /messages] ⚠️ 알 수 없는 메시지 타입 건너뜀: {type(msg_data)}")
                    continue # 다음 메시지로 넘어감

                # content가 비어있지 않은 경우에만 추가 (선택 사항)
                if content:
                    processed_messages.append(Message(role=role, content=content))
                else:
                    print(f"  [API /messages] ⚠️ 내용이 없는 메시지 건너뜀: role={role}")


            except Exception as e_msg_proc:
                # 개별 메시지 처리 오류는 로깅하고 계속 진행
                print(f"  [API /messages] ⚠️ 메시지 처리 중 오류: {e_msg_proc}, 메시지 데이터: {msg_data}")

        print(f"[API /messages] 세션 {session_id}에 대해 {len(processed_messages)}개의 메시지 반환.")
        return processed_messages

    except HTTPException: # 이미 HTTPException인 경우 그대로 전달
        raise
    except Exception as e:
        print(f"[API /messages] 세션 메시지 조회 중 예기치 않은 오류: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메시지 기록 조회 중 예기치 않은 오류 발생: {e}"
        )


@router.post("/sessions/{session_id}/restore", tags=["Session Management"])
async def restore_session_api(session_id: str): # 함수 이름 충돌 방지
    """ SQL 등 영구 저장소에서 Redis로 세션 상태 복원 시도 """
    print(f"[API /restore] 세션 {session_id} 복구 요청")
    try:
        success = await restore_session_to_redis(session_id)
        if success:
            print(f"[API /restore] 세션 {session_id} 복구 성공")
            return {"success": True, "message": "세션 복구 성공"}
        else:
            print(f"[API /restore] 세션 {session_id} 복구 실패 (restore_session_to_redis가 False 반환)")
            # 실패 시 404 또는 다른 적절한 상태 코드 반환 고려
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없거나 복구에 실패했습니다.")
    except Exception as e:
        print(f"[API /restore] 세션 복구 중 오류 발생: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"세션 복구 중 오류 발생: {e}")


# --- Why Agent 관련 엔드포인트 ---

class WhyTurnRequest(BaseModel):
    input: str # 사용자 입력은 필수로 변경

@router.post("/sessions/{session_id}/why", response_model=MessageResponse, tags=["Why Agent"])
async def run_why_turn_endpoint(session_id: str, req: WhyTurnRequest = Body(...)): # 함수 이름 충돌 방지
    """ Why agent를 통한 탐색 턴 실행 """
    print(f"[API /why] 세션 {session_id} Why 턴 실행 요청: input='{req.input[:50]}...'")

    # 입력 값 검증 (Pydantic에서 이미 처리하지만 명시적으로도 가능)
    # if not req.input:
    #     raise HTTPException(status_code=400, detail="입력 내용이 필요합니다.")

    try:
        # run_why_exploration_turn 호출
        # initial_topic은 run_why_exploration_turn 내부에서 새 세션 여부 판단 후 사용됨
        response_content = await run_why_exploration_turn(
            session_id=session_id,
            user_input=req.input,
            initial_topic=req.input # 새 세션의 첫 턴일 경우 raw_topic 설정에 사용됨
        )

        # 오케스트레이터가 None을 반환하는 경우 처리
        if response_content is None:
            print(f"[API /why][WARN] run_why_exploration_turn이 None을 반환 (session: {session_id}).")
            # 사용자에게 전달할 적절한 메시지 설정
            response_content = "대화 흐름을 완료했거나 처리 중 문제가 발생했습니다. 다음 질문을 입력해주세요."
            # 또는 상태에 따라 다른 메시지 가능 (예: 최종 요약이 있다면 그것을 반환)

        print(f"[API /why] 세션 {session_id} 응답 반환: '{response_content[:50]}...'")
        return MessageResponse(content=response_content)

    except GraphInterrupt as gi:
        # LangGraph 노드가 사용자 입력을 기다리기 위해 interrupt 발생시킨 경우
        interrupt_message = str(gi.value) if gi.value else "다음 입력을 기다리고 있습니다."
        print(f"[API /why][INFO] GraphInterrupt 발생 (session: {session_id}): '{interrupt_message[:50]}...'")
        # GraphInterrupt의 value는 노드가 사용자에게 전달하려는 메시지/질문
        return MessageResponse(content=interrupt_message)

    except HTTPException: # 이미 HTTPException인 경우 그대로 전달
        raise
    except Exception as e:
        # 예상치 못한 오류 발생 시
        print(f"[API /why][ERROR] Why 흐름 처리 중 예외 발생 (session: {session_id}): {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Why 흐름 처리 중 예기치 않은 오류 발생: {e}"
        )

