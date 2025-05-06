# backend/app/core/user_state.py
"""
UserStateStore: 사용자 대화 상태 및 전체 대화 로그(transcript)를 SQL DB에 저장/로드합니다.
"""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session_async
from app.db.models import SessionStateRecord, SessionTranscriptRecord


class UserStateStore:
    """
    사용자 상태(state)와 대화 로그(transcript)를 관리하는 저장소입니다.
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory  # 외부에서 주입

    async def load(self, session_id: str) -> dict:
        async with self._session_factory() as session:  # type: AsyncSession
            result = await session.execute(
                select(SessionStateRecord).where(SessionStateRecord.session_id == session_id)
            )
            record = result.scalar_one_or_none()
            return record.state if record else {}

    async def upsert(self, session_id: str, state: dict) -> None:
        async with self._session_factory() as session:  # type: AsyncSession
            result = await session.execute(
                select(SessionStateRecord).where(SessionStateRecord.session_id == session_id)
            )
            record = result.scalar_one_or_none()
            if record:
                record.state = state
                record.updated_at = datetime.utcnow()
            else:
                session.add(SessionStateRecord(
                    session_id=session_id,
                    state=state,
                ))
            await session.commit()

    async def append_transcript(self, session_id: str, role: str, content: str) -> None:
        async with self._session_factory() as session:  # type: AsyncSession
            session.add(SessionTranscriptRecord(
                session_id=session_id,
                role=role,
                content=content,
            ))
            await session.commit()
