# backend/app/core/state_manager.py
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

# TODO: 이 모듈은 LangGraph 체크포인트 메커니즘 (DB, Redis 등)으로 대체하는 것이 장기적으로 바람직함.
#       현재는 초기 세션 정보(주제, 초기 에이전트)를 임시 저장하는 용도로만 사용.

_SESSION_TTL = timedelta(hours=1)

# 저장 구조: {'session_id': {'topic': str, 'agent_type': str, 'created_at': datetime}}
_session_initial_info: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

def _is_expired(session_info: Dict[str, Any]) -> bool:
    return datetime.utcnow() - session_info.get("created_at", datetime.utcnow()) > _SESSION_TTL

def create_new_session(topic: str, initial_agent_type: Optional[str] = None) -> str:
    """ 새로운 세션 ID를 생성하고 초기 정보(주제, 에이전트 타입)를 메모리에 저장합니다. """
    new_session_id = str(uuid.uuid4())
    session_info = {
        "topic": topic,
        "agent_type": initial_agent_type or "critic", # 기본값 critic
        "created_at": datetime.utcnow(),
    }
    with _lock:
        _session_initial_info[new_session_id] = session_info
    print(f"세션 초기 정보 저장됨 (메모리): ID={new_session_id}, 주제='{topic}', 초기 에이전트='{session_info['agent_type']}'")
    return new_session_id

def get_session_initial_info(session_id: str) -> Optional[Dict[str, Any]]:
    """ 세션 ID로 초기 정보(주제, 에이전트 타입)를 가져옵니다. """
    with _lock:
        session_info = _session_initial_info.get(session_id)
        if not session_info or _is_expired(session_info):
            if session_info:
                del _session_initial_info[session_id]
                print(f"만료된 세션 초기 정보 삭제됨: ID={session_id}")
            return None
        # created_at은 제외하고 반환
        return {"topic": session_info.get("topic"), "agent_type": session_info.get("agent_type")}

def delete_session_initial_info(session_id: str) -> bool:
    """ 세션 초기 정보를 메모리에서 제거합니다. """
    with _lock:
        if session_id in _session_initial_info:
            del _session_initial_info[session_id]
            print(f"세션 초기 정보 삭제됨 (메모리): ID={session_id}")
            return True
        return False

# --- get_session_topic, get_session_initial_agent 함수는 get_session_initial_info 로 대체 ---
# def get_session_topic(session_id: str) -> Optional[str]: ...
# def get_session_initial_agent(session_id: str) -> Optional[str]: ...

# --- AutoGen 상태 관련 함수들은 제거 또는 주석 처리 ---
# def get_session_autogen_state(...): ...
# def save_session_autogen_state(...): ...